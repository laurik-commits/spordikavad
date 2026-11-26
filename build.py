"""Kogub andmed kõigist allikatest ja genereerib staatilise lehe kausta dist/.

Kasutus:
    python build.py            # kogub andmed ja ehitab lehe
    python build.py --offline  # ainult ehitab lehe data/ kausta viimastest andmetest
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import logging
import re
import shutil
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import archive
import ulekanded
from scrapers import config as cfgmod
from scrapers import sports
from scrapers.geo import Geo, Region
from scrapers.http import Fetcher
from scrapers.model import DEFAULT_LEVEL, EVENT_SPORTS, LEVELS, SPORTS, TALLINN, Event, levels_for
from scrapers.venues import Venues

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
DIST = ROOT / "dist"
REPORT = ROOT / "build_report.json"

log = logging.getLogger("build")

WEEKDAYS = ["esmaspäev", "teisipäev", "kolmapäev", "neljapäev", "reede", "laupäev", "pühapäev"]
SHORT_WEEKDAYS = ["E", "T", "K", "N", "R", "L", "P"]
MONTHS_IN = ["jaanuaris", "veebruaris", "märtsis", "aprillis", "mais", "juunis", "juulis",
             "augustis", "septembris", "oktoobris", "novembris", "detsembris"]
# ala omastav ("Tallinnas pole … jalgpalli mänge"), seesütlev ("Ela kaasa koondistele jalgpallis Tallinnas"),
# rühmad päise alavalikus, nimi värvilises kellaplokis, allikate lingid ja käsitsi kaetud märkused:
# kõik tulevad alade registrist sports.toml (scrapers/sports.py). Uue ala lisamiseks piisab ühest plokist seal.
SPORT_GEN = sports.GEN
SPORT_IN = sports.IN
# rühma nimi valib kõik selle alad, nool avab üksikud alad (site/app.js).
# Rühm on menüüs ainult siis, kui sellel tasemel on vähemalt 2 selle rühma ala; muidu on ala eraldi.
SPORT_GROUPS = sports.groups()


def sport_menu(filters: list[dict]) -> list[dict]:
    """Alavaliku read: rühmad (SPORT_GROUPS järjekorras) ja siis rühmata alad (filtrite järjekorras).
    Rühm: {"group": {..., "count", "sports"}, "members": [filter, ...]}; üksik ala: {"item": filter}.
    (Võti pole "items": Jinja loeks m.items sõnastiku meetodina.)"""
    by_key = {f["key"]: f for f in filters}
    menu, used = [], set()
    for g in SPORT_GROUPS:
        members = [by_key[s] for s in g["sports"] if s in by_key]
        if len(members) >= 2:
            menu.append({"group": dict(g, count=sum(m["count"] for m in members),
                                       sports=[m["key"] for m in members]), "members": members})
            used.update(m["key"] for m in members)
    menu += [{"item": f} for f in filters if f["key"] not in used]
    return menu


# ala nimi värvilises kellaplokis: pikkadesse sõnadesse pehme sidekriips (registris `block`)
SPORT_BLOCK = sports.BLOCK
MONTHS = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli",
          "august", "september", "oktoober", "november", "detsember"]


# --- Kogumine ---------------------------------------------------------------

def _data_file(name: str) -> Path:
    return DATA / f"{name}.json"


def load_saved(name: str) -> list[Event]:
    path = _data_file(name)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Event.from_dict(d) for d in raw["events"]]


def save(name: str, events: list[Event]) -> None:
    """Salvestab allika andmed. Kui mängud pole muutunud, faili ei puudutata (siis pole ka igapäevast commit'i)."""
    DATA.mkdir(exist_ok=True)
    rows = [e.to_dict() for e in sorted(events, key=lambda e: (e.start, e.id))]
    path = _data_file(name)
    if path.exists():
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("events") == rows:
                return
        except ValueError:
            pass
    payload = {"updated": datetime.now(TALLINN).isoformat(timespec="seconds"), "events": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


UPCOMING_DAYS = 42  # hooaja sees peab igal võistlusel olema mänge selle aja jooksul (talvepaus mahub sisse)


def missing_upcoming(src: dict, fetched: list[Event], today: date) -> list[str]:
    """Võistlused, millel on hooaja sees järgmise UPCOMING_DAYS päeva jooksul 0 mängu.

    Möödunud mänge ei arvestata: kui uuel hooajal liiga ID muutub, näitab vana leht ikka eelmise hooaja
    mänge ja ilma selle kontrollita kaoks liiga vaikselt. Võistlus `check = false` (karikad, playoffid) jäetakse välja.
    """
    if src.get("manual") or not src.get("check", True) or not cfgmod.in_season(src, today):
        return []  # käsitsi lisatud üritusi võib vahepeal mitte olla
    horizon = today + timedelta(days=UPCOMING_DAYS)

    def has_upcoming(league: str | None) -> bool:
        return any(today <= e.start.date() <= horizon and (league is None or e.league == league) for e in fetched)

    comps = src.get("competitions")
    if not comps:
        return [] if has_upcoming(None) else [src.get("league", src["name"])]
    return [c["league"] for c in comps
            if c.get("check", True) and cfgmod.in_season(c, today, src) and not has_upcoming(c["league"])]


def only_estonia(events: list[Event], venues: Venues, geo: Geo, today: date | None = None,
                 entry: dict | None = None) -> list[Event]:
    """Jätab alles Eestis toimuvad mängud (välismaa saalid välja) ja normaliseerib saali nime ja linna.

    Lähipäevade mängud, millel saal üldse puudub, loetakse kokku (entry["no_venue"]), et need ei kaoks vaikselt.
    """
    out = []
    window_end = today + timedelta(days=15) if today else None
    for e in events:
        if e.venue.strip() in geo.foreign:
            continue  # üritusekalendrites on välismaa võistlusel koha asemel ainult linn ("Kaunas")
        if not e.venue.strip():
            if entry is not None and today and today <= e.start.date() <= window_end:
                entry.setdefault("no_venue", []).append(f"{e.start:%d.%m %H:%M} {matchup(e)} ({e.league})")
            continue
        v = venues.lookup(e.venue)
        if v is not None and geo.is_estonian(v.city):
            out.append(replace(e, venue=v.name, city=v.city))
    return out


def collect(cfg: dict, venues: Venues, fetcher: Fetcher | None, today: date,
            geo: Geo | None = None, archive_root: Path | None = None,
            videos: dict[str, dict] | None = None) -> tuple[list[Event], list[dict]]:
    """Tagastab kõik Eesti mängud ja aruande iga allika kohta.

    Ühe allika viga ei peata ehitust: siis kasutatakse selle allika viimaseid salvestatud andmeid.
    `videos`: siia kogutakse ülekande lingid mängudelt, mis andmetesse ei jäänud (nt kasipall.ee peetud
    mängul pole saali, mäng tuleb lehele arhiivist) → data/ulekanded.json, vt ulekanded.apply.
    """
    geo = geo or Geo(cfg)
    all_events: list[Event] = []
    report: list[dict] = []
    for src in cfg.get("source", []):
        name = src["name"]
        if not src.get("enabled", True):
            continue
        entry = {"source": name, "status": "ok", "fetched": 0, "saved": 0, "error": ""}
        events: list[Event] | None = None
        if fetcher is None:
            entry["status"] = "offline"
        else:
            try:
                module = importlib.import_module(f"scrapers.{name}")
            except ModuleNotFoundError:
                entry["status"] = "no_adapter"
                module = None
            if module is not None:
                try:
                    # adapter, mis vajab config.toml-i rida (nt võistluste nimekirja), saab selle kaasa
                    wants_source = "source" in inspect.signature(module.fetch).parameters
                    fetched = module.fetch(fetcher, source=src) if wants_source else module.fetch(fetcher)
                    entry["fetched"] = len(fetched)
                    missing = missing_upcoming(src, fetched, today)
                    checked = [c for c in src.get("competitions", [{}])
                               if c.get("check", True) and cfgmod.in_season(c, today, src)]
                    if missing and len(missing) >= len(checked):
                        # ükski võistlus ei andnud tulevasi mänge → kasuta viimaseid salvestatud andmeid
                        entry["status"] = "empty"
                        entry["error"] = f"Hooaja sees {UPCOMING_DAYS} päeva jooksul 0 mängu"
                    else:
                        if missing:
                            entry["status"] = "partial"
                            entry["error"] = (f"Hooaja sees {UPCOMING_DAYS} päeva jooksul 0 mängu: "
                                              + ", ".join(missing) + ". Kas liiga ID on muutunud?")
                        events = only_estonia(fetched, venues, geo, today, entry)
                        if videos is not None:
                            kept = {e.id for e in events}
                            videos.update({e.id: ulekanded.link_of(e) for e in fetched
                                           if e.video and e.id not in kept})
                        save(name, events)
                        try:
                            archive.update(name, events, today, complete=entry["status"] == "ok",
                                           root=archive_root or archive.ARCHIVE)
                        except Exception:  # noqa: BLE001 - arhiivi viga ei tohi lehe ehitust takistada
                            log.exception("%s: arhiveerimine ebaõnnestus", name)
                except Exception as exc:  # noqa: BLE001 - ükski adapter ei tohi ehitust katki teha
                    entry["status"] = "failed"
                    entry["error"] = f"{type(exc).__name__}: {exc}"
                    log.exception("%s ebaõnnestus", name)
        if events is None:
            events = load_saved(name)
            if entry["status"] in ("failed", "empty", "partial"):
                log.warning("%s: kasutan viimaseid salvestatud andmeid (%d mängu)", name, len(events))
        entry["saved"] = len(events)
        all_events.extend(events)
        report.append(entry)
    return all_events, report


# --- Genereerimine ----------------------------------------------------------

def et_date(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]}"


def when_where(e: Event) -> str:
    """Jagamise ja eelvaate tekst: "laupäev, 21. november kell 19:00, Kalevi spordihall, Tallinn".
    Mitmepäevane üritus: "reede, 13. november – laupäev, 14. november, Unibet Arena, Tallinn"."""
    if e.end:
        when = f"{et_date(e.start.date())} – {et_date(e.last_day)}"
    else:
        when = et_date(e.start.date()) + ("" if e.time_tbc else f" kell {e.start:%H:%M}")
    place = ", ".join(dict.fromkeys(x for x in (e.venue, e.city) if x))  # "Pärnu, Pärnu" → "Pärnu"
    return f"{when}, {place}" if place else when


def matchup(e: Event) -> str:
    """ "Kalev – Valmiera"; turniiril või eriüritusel (külalisi pole, käsitsi lisatud) ainult ürituse nimi."""
    return f"{e.home} – {e.away}" if e.away else e.home


def event_day(e: Event, d: date) -> str:
    """Mitmepäevase ürituse kellaplokk alates teisest päevast: "2./3. päev". Muidu tühi (näidatakse kellaaega)."""
    if not e.end or d <= e.start.date():
        return ""
    return f"{(d - e.start.date()).days + 1}./{(e.last_day - e.start.date()).days + 1}. päev"


def date_span(e: Event) -> str:
    """Mitmepäevase ürituse kuupäevad real: "13.–14.11" või "30.11–2.12". Ühepäevasel tühi."""
    if not e.end:
        return ""
    a, b = e.start.date(), e.last_day
    return f"{a.day}.–{b.day}.{b.month:02d}" if a.month == b.month else f"{a.day}.{a.month:02d}–{b.day}.{b.month:02d}"


def share_text(e: Event) -> str:
    """Tekst, mis läheb jagatava lingi juurde: "Kalev – Valmiera: laupäev, 21. november kell 19:00, ..."."""
    return f"{matchup(e)}: {when_where(e)}"


def calendar_data(events: list[Event], first: date, last: date, today: date, geo: Geo,
                  channel_types: dict[str, str], also: dict[str, list[dict]] | None = None) -> dict:
    """kalender.json: kõik mängud alates `first` (möödunud päevad) kuni kaugeima tulevaseni, lühikeste võtmetega.
    Seda loeb site/kalender.js nädala ja kuu vaate, kuupäeva valiku ja 14 päevast kaugemate päevade jaoks.
    `first`/`last` = staatiliste päevalehtede vahemik (mängulehed /m/<id>/ on ainult selle sees)."""
    rows = []
    for e in sorted(events, key=lambda e: (e.start, e.id)):
        if e.last_day < first:
            continue
        region = geo.region_of(e.city)
        r = {"id": e.id, "s": e.sport, "l": e.league, "t": e.start.isoformat()[:16], "h": e.home, "a": e.away,
             "v": e.venue, "c": e.city, "u": e.url, "lv": e.level, "rg": region.slug if region else "",
             "sh": share_text(e)}
        if e.time_tbc:
            r["tbc"] = 1
        if e.result:
            r["r"] = e.result
        if e.note:
            r["n"] = e.note
        if e.end:
            r["e"], r["sp"] = e.end, date_span(e)
        if e.video:
            r["vid"], r["vb"], r["vk"] = e.video, e.video_by, channel_types.get(e.video_by, "veeb")
            more = (also or {}).get(e.id)
            if more and not e.end and today <= e.start.date() <= last:
                # mitu kanalit: ikoon viib mängu lehele, kus on kõik ülekande nupud
                r["vid"], r["vb"] = f"m/{e.id}/", ", ".join([e.video_by] + [a["video_by"] for a in more])
        rows.append(r)
    return {"today": today.isoformat(), "first": first.isoformat(), "last": last.isoformat(),
            "hidden": [k for k, v in LEVELS.items() if v.get("hidden")], "events": rows}


def _norm_team(name: str) -> str:
    return re.sub(r"[^\w]+", " ", name.lower()).strip()


def dedupe(events: list[Event]) -> tuple[list[Event], int]:
    """Eemaldab sama mängu, mis tuleb mitmest allikast (nt Balti liiga mäng on ka kasipall.ee-s).

    Sama mäng = sama ala ja algusaeg ning kas samad võistkonnad VÕI sama saal (allikad kirjutavad
    võistkondi eri moodi, nt "KPK Mella" / "Käsipalliklubi Mella", aga ühes saalis ei saa samal ajal
    kaht mängu olla). Alles jääb esimene (config.toml allikate järjekord). Kui alles jäänul pole
    ülekande linki, aga eemaldatul on, võetakse link eemaldatult."""
    seen: dict[tuple, int] = {}  # võti → koht `out` loendis
    out: list[Event] = []
    for e in events:
        keys = [("teams", e.sport, e.start, _norm_team(e.home), _norm_team(e.away))]
        if e.venue:
            keys.append(("venue", e.sport, e.start, e.venue))
        hit = next((seen[k] for k in keys if k in seen), None)
        if hit is not None:
            if e.video and not out[hit].video:
                out[hit] = replace(out[hit], video=e.video, video_by=e.video_by)
            continue
        seen.update((k, len(out)) for k in keys)
        out.append(e)
    return out, len(events) - len(out)


def regions_for(events: list[Event], geo: Geo) -> list[Region]:
    """Valiku järjekord: Kogu Eesti, Tallinn, teised linnad mängude arvu järgi, siis maakonnad.
    Linn või maakond on valikus, kui selle kohta on hooaja andmetes vähemalt üks mäng (Tallinn alati)."""
    counts: dict[str, int] = {}
    for e in events:
        r = geo.region_of(e.city)
        if r:
            counts[r.slug] = counts.get(r.slug, 0) + 1
    pinned = [r for r in geo.city_regions.values() if r.slug == "tallinn"]
    cities = sorted((r for r in geo.city_regions.values() if r not in pinned and counts.get(r.slug)),
                    key=lambda r: (-counts[r.slug], r.name))
    counties = sorted((r for r in geo.county_regions.values() if counts.get(r.slug)), key=lambda r: r.name)
    return [geo.all, *pinned, *cities, *counties]


TITLE_MAX = 72     # mängulehe pealkirja pikkus (otsingutulemus lõikab pikema ära)
LIST_LIMIT = 150   # ala- ja liigalehel nähtavate tulevaste mängude arv (ülejäänud: liigalehed)
SHORT_MONTHS = ["jaan", "veebr", "märts", "apr", "mai", "juuni", "juuli", "aug", "sept", "okt", "nov", "dets"]
_ASCII = str.maketrans({"ä": "a", "ö": "o", "õ": "o", "ü": "u", "š": "s", "ž": "z", "é": "e", "ō": "o", "ā": "a",
                        "ē": "e", "ī": "i", "ū": "u", "ļ": "l", "ņ": "n", "ķ": "k", "ģ": "g", "č": "c"})


def slugify(text: str) -> str:
    """„Eesti-Läti Korvpalliliiga“ → „eesti-lati-korvpalliliiga“ (URL-i osa, ainult a–z, 0–9 ja sidekriips)."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(_ASCII)).strip("-")
    return s[:60].strip("-") or "liiga"


def game_title(e: Event, score: str = "") -> str:
    """Mängulehe pealkiri: „Kodu – Külaline | Liiga | 28. nov 19:00 | Toimumiskoht“ (kõige olulisem ees)."""
    when = f"{e.start.day}. {SHORT_MONTHS[e.start.month - 1]}"
    if not e.time_tbc and not e.end:
        when += f" {e.start:%H:%M}"
    name = matchup(e) + (f" {score}" if score else "")
    place = e.venue or e.city
    # otsingutulemuses jääb nähtavale ~60–70 märki: kõigepealt jääb ära koht, siis liiga, viimaks lõigatakse nimi
    for parts in ((name, e.league, when, place), (name, e.league, when), (name, when)):
        title = " | ".join(x for x in parts if x)
        if len(title) <= TITLE_MAX:
            return title
    return title[:TITLE_MAX - 1].rsplit(" ", 1)[0].rstrip(" |,–-") + "…"


def event_ld(e: Event, url: str) -> str:
    """schema.org SportsEvent (JSON-LD) mängulehele. Võistkonnad ainult meeskonnamängul; koht ainult siis, kui see on teada;
    kellaajata mängul ainult kuupäev."""
    start = e.start.date().isoformat() if e.time_tbc else e.start.isoformat(timespec="minutes")
    data: dict = {"@context": "https://schema.org", "@type": "SportsEvent", "name": matchup(e), "url": url,
                  "startDate": start, "sport": SPORTS[e.sport],
                  "eventStatus": "https://schema.org/EventScheduled",
                  "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                  "description": f"{SPORTS[e.sport]}, {e.league}"}
    if e.end:
        data["endDate"] = e.end
    if e.venue or e.city:
        place: dict = {"@type": "Place", "name": e.venue or e.city}
        if e.city:
            place["address"] = {"@type": "PostalAddress", "addressLocality": e.city, "addressCountry": "EE"}
        data["location"] = place
    if e.away and e.sport not in EVENT_SPORTS:
        data["homeTeam"] = {"@type": "SportsTeam", "name": e.home}
        data["awayTeam"] = {"@type": "SportsTeam", "name": e.away}
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render(events: list[Event], cfg: dict, today: date, out: Path = DIST,
           watch: dict[tuple[str, str], list[dict]] | None = None,
           channel_types: dict[str, str] | None = None, also: dict[str, list[dict]] | None = None,
           all_games: list[Event] | None = None) -> int:
    """all_games: lisaks `events`-ile kõik teadaolevad (möödunud) mängud arhiivist: neile tehakse mängulehed.
    watch: (ala, liiga) → ülekandjad (ulekanded.league_channels); mängu lehel „Selle liiga mänge on näidanud“.
    channel_types: kanal → "tv" / "veeb" (ulekanded.channel_types): ülekande ikoon ja tekst."""
    watch = watch or {}
    channel_types = channel_types if channel_types is not None else ulekanded.channel_types(ulekanded.load())
    site_cfg = cfg.get("site", {})
    default_level = int(site_cfg.get("default_level", DEFAULT_LEVEL))
    levels = levels_for(default_level)
    days_ahead = int(site_cfg.get("days_ahead", 14))
    base_url = site_cfg.get("base_url", "").rstrip("/") + "/"
    days_back = int(site_cfg.get("days_back", 14))  # möödunud päevad jäävad nähtavale (mängud arhiivist)
    days = [today + timedelta(days=i) for i in range(-days_back, days_ahead + 1)]
    today_i = days_back  # tänase päeva koht `days` loendis (avaleht, kanooniline aadress)
    geo = Geo(cfg)
    regions = regions_for(events, geo)

    def in_region(e: Event, r: Region) -> bool:
        if r.kind == "all":
            return True
        er = geo.region_of(e.city)
        return er is not None and er.slug == r.slug

    links = [{"sport": l["sport"], "label": SPORTS[l["sport"]], "url": l["url"],
              "note": l.get("note", ""), "link_text": l.get("link_text", "")} for l in cfg.get("external_link", [])]
    sport_notes = {n["sport"]: n for n in cfg.get("sport_note", [])}
    external = {l["sport"] for l in links}

    # millised alad on igal tasemel olemas (filtrinupud on alati nähtaval, ka siis kui mänge pole)
    cov = coverage(cfg)
    sports_at = {1: [r["key"] for r in cov if r["top"] and r["key"] not in external],
                 2: [r["key"] for r in cov if r["low"] and r["key"] not in external],
                 3: [r["key"] for r in cov if r["minor"] and r["key"] not in external],
                 4: [r["key"] for r in cov if r["youth"] and r["key"] not in external],
                 5: [r["key"] for r in cov if r["national"] and r["key"] not in external]}
    # "Kõik liigad": kõigi nähtavate tasemete alad, igaüks korra, tabeli järjekorras
    sports_at[0] = [k for k in dict.fromkeys(s for lvl, lv in LEVELS.items()
                                              if lvl in sports_at and not lv.get("hidden") for s in sports_at[lvl])]

    def on_level(e: Event, level: int) -> bool:
        if LEVELS[level].get("all"):
            return not LEVELS[e.level].get("hidden")
        return e.level == level

    def offseason_note(sport: str) -> str:
        """Kui ala ükski allikas pole hooajas: "Jalgpalli hooaeg algab märtsis." """
        # terve aasta allikad (koondised) ei ütle midagi liigahooaja kohta
        srcs = [s for s in cfg.get("source", [])
                if s.get("enabled", True) and s.get("sport") == sport and not s.get("year_round")]
        if not srcs or any(cfgmod.in_season(s, today) for s in srcs):
            return ""
        starts = sorted(int(start[-5:-3]) for s in srcs for start, _ in s.get("seasons", []))
        upcoming = [m for m in starts if m > today.month] or starts
        return f"{SPORT_GEN[sport].capitalize()} hooaeg algab {MONTHS_IN[upcoming[0] - 1]}." if upcoming else ""

    env = Environment(loader=FileSystemLoader(SITE), autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["et_date"] = et_date
    env.filters["share_text"] = share_text
    env.filters["matchup"] = matchup
    env.filters["when_where"] = when_where
    env.filters["event_day"] = event_day
    env.filters["date_span"] = date_span
    env.filters["watch"] = lambda e: watch.get((e.sport, e.league), [])
    env.filters["also"] = lambda e: (also or {}).get(e.id, [])
    env.filters["watch_kind"] = lambda e, past: ulekanded.watch_kind(e.video_by, past, channel_types)
    env.filters["watch_kind_by"] = lambda by: ulekanded.watch_kind(by, False, channel_types or {})
    tpl = env.get_template("day.html")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for asset in ("app.js", "og.png", "paise.webp"):
        shutil.copy(SITE / asset, out / asset)
    for asset in ("style.css", "kalender.js"):  # alade värvid ja nimed tulevad registrist (sports.toml)
        (out / asset).write_text(sports.fill((SITE / asset).read_text(encoding="utf-8")), encoding="utf-8")

    # mängud päeva kaupa (14 päeva aken)
    # mitmepäevane üritus on igal oma päeval
    window = {d: [] for d in days}
    for e in events:
        d = e.start.date()
        while d <= e.last_day:
            if d in window:
                window[d].append(e)
            d += timedelta(days=1)

    def order(e: Event, d: date) -> tuple:
        # kellaajaga read kellaaja järgi; kellaajata ja mitmepäevase ürituse järgmised päevad lõpus
        later = e.start.date() < d
        return (e.time_tbc or later, e.start.time() if not later else datetime.min.time(), e.sport, e.home)

    def by_day_for(level: int, r: Region) -> dict[date, list[Event]]:
        return {d: sorted((e for e in window[d] if on_level(e, level) and in_region(e, r)),
                          key=lambda e, d=d: order(e, d)) for d in days}

    now = datetime.now(TALLINN)
    common = dict(
        sports=SPORTS, sport_in=SPORT_IN, event_sports=EVENT_SPORTS, links=links, sport_notes=sport_notes, today=today, default_slug=Geo.default_slug, default_level=default_level,
        level_prefixes=json.dumps({str(k): v["prefix"] for k, v in levels.items()}),
        updated=f"{now.day}.{now.month:02d} kell {now:%H:%M}", built=today.isoformat(),
        analytics_enabled=site_cfg.get("analytics_enabled", False),
        analytics_token=site_cfg.get("analytics_token", ""), base_url=base_url,
        google_verification=site_cfg.get("google_site_verification", ""),
        contact_url=site_cfg.get("contact_url", ""), watch_types=ulekanded.TYPES,
        sport_block={k: SPORT_BLOCK.get(k, v) for k, v in SPORTS.items()},
    )

    urls: list[str] = []
    for level, lv in levels.items():
        # samad piirkonnad mõlemal tasemel, et linna/taseme vahetus ei viiks olematule lehele
        region_days = {r.slug: by_day_for(level, r) for r in regions}
        # valikute numbrid: tulevased mängud (täna + 14 päeva), möödunud päevi ei loeta
        region_list = [{"slug": r.slug, "name": r.name, "prefix": r.prefix, "kind": r.kind,
                        "count": sum(len(v) for d, v in region_days[r.slug].items() if d >= today)} for r in regions]
        level_list = [{"level": k, "name": v["name"], "prefix": v["prefix"], "current": k == level,
                       "count": sum(1 for d in days if d >= today for e in window[d] if on_level(e, k))}
                      for k, v in levels.items() if not v.get("hidden") or k == level]
        for r in regions:
            by_day = region_days[r.slug]
            present: dict[str, int] = {}  # ala → tulevaste mängude arv (täna + 14 päeva)
            for d, lst in by_day.items():
                if d >= today:
                    for e in lst:
                        present[e.sport] = present.get(e.sport, 0) + 1
            filters = []
            for s in sports_at[level]:
                if s in present:
                    filters.append({"key": s, "label": SPORTS[s], "none": False, "msg": "", "count": present[s]})
                else:
                    # "saalihokimänge" (kõik liigad) või "saalihoki tippvõistlusi"
                    if s in EVENT_SPORTS:  # "motospordivõistlusi" (üritustel pole liigasid)
                        games = f"{SPORT_GEN[s]}võistlusi"
                    else:
                        games = f"{SPORT_GEN[s]}mänge" if lv.get("all") else f"{SPORT_GEN[s]} {lv['many']}"
                    msg = offseason_note(s) or f"Järgmise kahe nädala jooksul ei ole {r.in_form} {games}."
                    filters.append({"key": s, "label": SPORTS[s], "none": True, "msg": msg, "count": 0})
            day_list = [{"date": d, "label": et_date(d), "short": SHORT_WEEKDAYS[d.weekday()],
                         "past": d < today, "count": len(by_day[d]),
                         "sports": sorted({e.sport for e in by_day[d]})} for d in days]
            prefix = lv["prefix"] + r.prefix
            rdir = out / prefix if prefix else out
            rdir.mkdir(parents=True, exist_ok=True)
            depth = prefix.count("/")  # mitu kausta sügavamal kui lehe juur
            for i, d in enumerate(days):
                ctx = dict(
                    common, region=r, regions=region_list, level=level, level_info=lv, levels=level_list,
                    show_city=r.kind != "city",
                    filters=filters, sport_menu=sport_menu(filters), days=day_list,
                    day=d, past=d < today, events=by_day[d],
                    prev_day=days[i - 1] if i > 0 else None,
                    next_day=days[i + 1] if i + 1 < len(days) else None,
                    next_games=next((x for x in days[i + 1:] if x >= today and by_day[x]), None),
                )
                page_dir = rdir / d.isoformat()
                page_dir.mkdir()
                index_url = f"{base_url}{prefix}"
                url = f"{base_url}{prefix}{d.isoformat()}/"
                # tänase päeva kuupäevaleht on sama sisu mis piirkonna avaleht → kanooniline on avaleht
                (page_dir / "index.html").write_text(
                    tpl.render(ctx, root="../" * (depth + 1), here="../", canonical=index_url if i == today_i else url,
                               is_index=False),
                    encoding="utf-8")
                # sitemap: avalehed alati, kuupäevalehed ainult siis, kui seal on mänge (tühje lehti ei pakuta);
                # möödunud päevi ei paku (neil on noindex)
                # "Kõik liigad" kordab teiste tasemete sisu: otsingumootorile ei paku
                if i > today_i and by_day[d] and not lv.get("all"):
                    urls.append(url)
                if i == today_i:
                    (rdir / "index.html").write_text(
                        tpl.render(ctx, root="../" * depth, here="", canonical=index_url, is_index=True),
                        encoding="utf-8")
                    if not lv.get("all"):
                        urls.append(index_url)

    # --- mängulehed /m/<id>/ ja ala- ja liigalehed (/<ala>/, /<ala>/<liiga>/) ---
    # Mängulehed on KÕIGIL teadaolevatel mängudel: tulevastel (ka päevaakna taga) ja möödunud mängudel arhiivist
    # (link ei anna 404, leht on „toimunud“, noindex). Ala- ja liigalehed loetlevad eelseisvad mängud ja on
    # mängulehtede sisemiste linkide siht. Peidetud tasemete (level 3) mänge ala- ja liigalehtedel pole.
    all_game_events: dict[str, Event] = {}
    for e in list(all_games or []) + list(events):
        all_game_events[e.id] = e   # praegused andmed (events) on viimane ja kirjutavad arhiivi kirje üle

    def listed(e: Event) -> bool:
        return not LEVELS[e.level].get("hidden")

    reserved = {"m", "info", *(lv["slug"] for lv in LEVELS.values()), *(r.slug for r in regions)}
    clash = reserved & set(SPORTS)
    if clash:
        raise ValueError(f"ala võti läheb vastuollu lehe kaustaga: {sorted(clash)}")
    leagues: dict[tuple[str, str], str] = {}   # (ala, liiga) → liiga kausta nimi alal
    taken: dict[str, set[str]] = {}
    for e in sorted(all_game_events.values(), key=lambda e: (e.sport, e.league)):
        if not listed(e) or (e.sport, e.league) in leagues:
            continue
        slug, n = slugify(e.league), 2
        while slug in taken.setdefault(e.sport, set()):
            slug, n = f"{slugify(e.league)}-{n}", n + 1
        taken[e.sport].add(slug)
        leagues[(e.sport, e.league)] = slug

    game_tpl = env.get_template("game.html")
    for e in sorted(all_game_events.values(), key=lambda e: (e.start, e.id)):
        past = e.last_day < today
        in_window = days[0] <= e.start.date() <= days[-1] or (e.start.date() < days[0] <= e.last_day)
        gd = max(e.start.date(), days[0]) if in_window else e.start.date()
        glv = levels[e.level]
        slug = leagues.get((e.sport, e.league))
        gdir = out / "m" / e.id
        gdir.mkdir(parents=True)
        canonical = f"{base_url}m/{e.id}/"
        (gdir / "index.html").write_text(
            game_tpl.render(common, e=e, root="../../", canonical=canonical, past=past, level_info=glv, day=gd,
                            day_href=f"../../{glv['prefix']}{geo.all.prefix}{gd.isoformat()}/" if in_window else "",
                            league_href=f"../../{e.sport}/{slug}/" if slug else (f"../../{e.sport}/" if listed(e) else ""),
                            title=game_title(e, e.result.replace("-", ":")), ld=event_ld(e, canonical)),
            encoding="utf-8")
        if not past and listed(e):
            urls.append(canonical)

    list_tpl = env.get_template("list.html")

    def sport_page(path: Path, root: str, canonical: str, heading: str, title: str, description: str,
                   rows: list[Event], subleagues: list[dict], parent: dict | None, sport: str) -> None:
        shown = rows[:LIST_LIMIT]
        path.mkdir(parents=True, exist_ok=True)
        (path / "index.html").write_text(
            list_tpl.render(common, root=root, canonical=canonical, heading=heading, title=title,
                            description=description, rows=shown, more=len(rows) - len(shown), subleagues=subleagues,
                            parent=parent, sport=sport, noindex=not rows),
            encoding="utf-8")
        if rows:
            urls.append(canonical)

    def next_text(rows: list[Event]) -> str:
        if not rows:
            return ""
        n = rows[0]
        return f" Järgmine: {matchup(n)}, {when_where(n)}."

    for sport, sport_name in SPORTS.items():
        sev = [e for e in all_game_events.values() if e.sport == sport and listed(e)]
        if not sev:
            continue
        one, many = ("võistlust", "võistlusi") if sport in EVENT_SPORTS else ("mängu", "mänge")
        plural = "võistlused" if sport in EVENT_SPORTS else "mängud"
        up = sorted((e for e in sev if e.last_day >= today), key=lambda e: (e.start, e.id))
        subs = []
        for (sp, league), slug in sorted(leagues.items(), key=lambda kv: kv[0][1]):
            if sp != sport:
                continue
            lup = sorted((e for e in sev if e.league == league and e.last_day >= today), key=lambda e: (e.start, e.id))
            subs.append({"name": league, "href": f"{slug}/", "count": len(lup)})
            desc = (f"{league}: {len(lup)} eelseisvat {one} Eestis." if lup
                    else f"{league}: eelseisvaid {many} praegu pole.") + next_text(lup)
            sport_page(out / sport / slug, "../../", f"{base_url}{sport}/{slug}/", league,
                       f"{league} ({sport_name.lower()}): ajakava ja eelseisvad {plural}", desc,
                       lup, [], {"name": sport_name, "href": "../"}, sport)
        desc = (f"{sport_name}: {len(up)} eelseisvat {one} Eestis, kohapeal vaatamiseks." if up
                else f"{sport_name}: eelseisvaid {many} praegu pole.") + next_text(up)
        sport_page(out / sport, "../", f"{base_url}{sport}/", sport_name,
                   f"{sport_name} Eestis: eelseisvad {plural} ja ajakava", desc, up, subs, None, sport)

    (out / "kalender.json").write_text(
        json.dumps(calendar_data(events, days[0], days[-1], today, geo, channel_types, also),
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    upcoming = sorted((e for e in events if e.start.date() >= today), key=lambda e: (e.start, e.id))
    (out / "events.json").write_text(
        json.dumps({"generated": datetime.now(TALLINN).isoformat(timespec="seconds"),
                    "events": [e.to_dict() for e in upcoming]}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # 404: vana kuupäevaleht (nt eilne) suunatakse sama piirkonna tänasele lehele
    base_path = "/" + base_url.split("://", 1)[1].split("/", 1)[1] if "://" in base_url else "/"
    (out / "404.html").write_text(env.get_template("404.html").render(common, base_path=base_path),
                                  encoding="utf-8")

    # „Meist“ leht
    info_dir = out / "info"
    info_dir.mkdir()
    (info_dir / "index.html").write_text(
        env.get_template("info.html").render(common, root="../", canonical=f"{base_url}info/",
                                             coverage=coverage(cfg), show_minor=not LEVELS[3].get("hidden"),
                                             watch_rows=ulekanded.rows(watch)),
        encoding="utf-8")
    urls.append(f"{base_url}info/")

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{u}</loc></url>" for u in urls]   # lastmod pole: tänane kuupäev kõigil poleks tõene
    sitemap.append("</urlset>")
    (out / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return len(urls)


# Allikate avalehed „Meist“ lehe jaoks: ala → [(nimi, URL), ...] (registris `sources`)
SOURCE_SITES = sports.SOURCE_SITES


# „Meist“ tabelis: alad või nende osad, mille suuremad võistlused lisatakse käsitsi (kasitsi.toml), mitte adapteriga
# (registris `manual`)
MANUAL_COVERAGE = sports.MANUAL_COVERAGE


def coverage(cfg: dict) -> list[dict]:
    """„Meist“ lehe tabel: ala, kõrgliigad (top), esiliigad (low), madalamad liigad (minor), noored (youth), koondised (national), allikas."""
    from scrapers import saalihoki_meistriliiga as floorball

    column = {1: "top", 2: "low", 3: "minor", 4: "youth", 5: "national"}
    rows: dict[str, dict] = {}
    for src in cfg.get("source", []):
        if not src.get("enabled", True) or src.get("manual"):
            continue  # käsitsi lisatud üritustel pole oma ala ega liigat
        sport = src["sport"]
        row = rows.setdefault(sport, {"key": sport, "sport": SPORTS[sport], "top": [], "low": [], "minor": [], "youth": [], "national": [],
                                      "source": SOURCE_SITES.get(sport, [])})
        if src.get("competitions"):
            for c in src["competitions"]:
                row[column[c.get("level", 1)]].append(c["league"])
        elif sport == "saalihoki":
            for league, level in floorball.LEAGUES.values():
                row[column[level]].append(league)
        else:
            row["top"].append(src.get("league", ""))
    for sport, text in MANUAL_COVERAGE.items():  # käsitsi (kasitsi.toml, otsinguagent) kaetud alad ja osad
        rows.setdefault(sport, {"key": sport, "sport": SPORTS[sport], "top": [], "low": [], "minor": [], "youth": [],
                                "national": [], "source": SOURCE_SITES.get(sport, [])})["top"].append(text)
    for row in rows.values():  # sama liiga mitmest allikast (nt Kalev ja Tartu Ülikool) ainult üks kord
        for col in column.values():
            row[col] = list(dict.fromkeys(row[col]))
    return [rows[s] for s in SPORTS if s in rows]


# --- Käivitamine ------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="ära tee võrgupäringuid")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    cfg = cfgmod.load()
    venues = Venues.load()
    today = datetime.now(TALLINN).date()
    http = cfg.get("http", {})
    fetcher = None if args.offline else Fetcher(
        cfgmod.user_agent(cfg), delay=http.get("delay", 3.0), host_delays=http.get("host_delays", {}),
        timeout=http.get("timeout", 20.0), retries=http.get("retries", 3))

    videos: dict[str, dict] = {}
    events, report = collect(cfg, venues, fetcher, today, videos=videos)
    try:
        # möödunud päevad (nt allikad, mis näitavad ainult tulevasi mänge): arhiivist; praegused andmed on eespool
        have = {e.id for e in events}
        events += [e for e in archive.past_events(today, int(cfg.get("site", {}).get("days_back", 14)))
                   if e.id not in have]
    except Exception:  # noqa: BLE001 - arhiivi viga ei tohi lehe ehitust takistada
        log.exception("möödunud mängude lugemine arhiivist ebaõnnestus")
    events, dupes = dedupe(events)
    if dupes:
        log.info("Eemaldasin %d topelt mängu (sama mäng mitmest allikast)", dupes)
    watch: dict = {}
    ul_cfg: dict = {}
    also: dict = {}
    try:
        ul_cfg = ulekanded.load()
        links = ulekanded.load_links()
        if fetcher is not None:
            # ülekandjate kavad (Delfi TV …) → mängude otseülekande lingid (data/ulekanded.json)
            streams, kava_report = ulekanded.fetch_streams(ul_cfg, fetcher)
            # kava rida, mida ühegi allika mäng ei kata ja mille koduhall on teada → mäng „kava järgi“
            games = ulekanded.unmatched_games(events, streams, ul_cfg)
            # saaliga mängud normaliseeritakse nagu muud; saalita mäng (koduhalli tabelis ainult linn) jääb saalita
            extra = only_estonia([e for e in games if e.venue], venues, Geo(cfg)) + [e for e in games if not e.venue]
            if extra:
                events, _ = dedupe(events + extra)
                log.info("Lisasin %d mängu ülekannete kava järgi", len(extra))
            new = ulekanded.match(events, streams + ulekanded.manual_streams(ul_cfg))
            # tulevaste päevade seos kustub, kui see enam kavas / ulekanded.toml-is pole (kavata kanalid
            # loetakse alati „värskeks“: nende allikas on ulekanded.toml ja mängude enda lingid)
            refreshed = ({r["channel"] for r in kava_report if r["status"] == "ok"}
                         | {k["nimi"] for k in ul_cfg.get("kanal", []) if not k.get("kava")})
            links = ulekanded.update_links(links, {**videos, **new}, today, refreshed)
            ulekanded.save_links(links)
            for r in kava_report:
                r["saved"] = sum(1 for v in new.values()
                                 if r["channel"] in [v["video_by"]] + [x["video_by"] for x in v.get("also", [])])
            report.extend(kava_report)
        events = ulekanded.apply(events, links)
        also = ulekanded.also(links)
        # kes mida näitab: käsitsi teadaolev (ulekanded.toml) + mängudest õpitu (arhiiv + praegused andmed)
        watch = ulekanded.league_channels(
            ul_cfg, ulekanded.apply(archive.past_events(today, ulekanded.LEARN_DAYS), links) + events)
    except Exception:  # noqa: BLE001 - ülekannete info viga ei tohi lehe ehitust takistada
        log.exception("ülekannete info koostamine ebaõnnestus")
    try:
        # möödunud mängud arhiivist: neile jäävad mängulehed alles (aadress ei anna 404)
        old_games = archive.past_events(today, 3650)
    except Exception:  # noqa: BLE001 - arhiivi viga ei tohi lehe ehitust takistada
        log.exception("arhiivi mängulehtede lugemine ebaõnnestus")
        old_games = []
    pages = render(events, cfg, today, watch=watch, channel_types=ulekanded.channel_types(ul_cfg), also=also,
                   all_games=old_games)
    REPORT.write_text(json.dumps({"date": today.isoformat(), "sources": report,
                                  "unknown_venues": sorted(venues.unknown)}, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    log.info("Kokkuvõte (%s):", today.isoformat())
    for r in report:
        extra = f" – {r['error']}" if r["error"] else ""
        log.info("  %-26s %-10s allikas %4d, Eestis %3d%s", r["source"], r["status"], r["fetched"], r["saved"], extra)
    if venues.unknown:
        log.info("  Tundmatud toimumiskohad: %s", ", ".join(sorted(venues.unknown)))
    log.info("  Lehti sitemapis: %d, mänge kokku: %d", pages, len(events))
    return 0


if __name__ == "__main__":
    sys.exit(main())
