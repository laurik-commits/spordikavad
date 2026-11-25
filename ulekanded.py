"""Ülekanded: kus mänge otse või järele näeb.

Kaks allikat:
1. Mängu enda link (`Event.video`, `Event.video_by`): adapter leiab selle allika lehelt (nt kasipall.ee
   „YouTube – järelvaatamine“) või ülekandja kavast. See on mängu real ja mängu lehel.
2. Liiga kaupa (`league_channels`): kes on selle liiga mänge näidanud. Siia läheb käsitsi teadaolev info
   (ulekanded.toml [[liiga]]) ja see, mida süsteem ise mängudest õpib: iga mäng, millel on `video_by`,
   lisab selle ülekandja oma liigale (arhiivist viimased LEARN_DAYS päeva). Nii täieneb nimekiri ise.

3. Ülekandja kava (`[[kanal]] kava = "delfi"` → scrapers/kava_delfi.py): kava read seotakse olemasolevate
   mängudega (`match`: ala, kellaaeg ±MATCH_MINUTES, võistkondade nimedes ühine sõna). Leitud seosed
   hoitakse failis data/ulekanded.json (mängu id → link), et ka möödunud päevadel ja õppimisel oleks see
   olemas. Kava ridu ei lisata mängudena, välja arvatud need, mille koduvõistkond on [[koduhall]] tabelis
   ja millega ükski olemasolev mäng ei seostu (punkt 5).

5. Kava-põhised mängud (`unmatched_games`): allikas, mis mängu ei näita (nt TalTechi kodumäng, Viimsi kodumäng),
   aga ülekandja kava näitab. Saal pärineb tabelist [[koduhall]], liiga on „<Ala> (kava järgi)“. Neid ei
   arhiveerita: kui mäng hiljem allika lehel ilmub, seostub kava rida sellega ja kava mängu enam ei teki.

4. Käsitsi teadaolev ülekanne (`[[mang]]`, lisab otsinguagent või omanik): käsitletakse nagu kava rida,
   seega seotakse ainult olemasoleva mänguga.

ulekanded.toml:
  [[kanal]]  ülekandja nimi (sama, mis `video_by`), leht, kuhu link viib, ja valikuliselt kava (adapter)
  [[liiga]]  sport + liigad (täpsed nimed) või liiga_algus (nimi algab nii, nt koondised) + kanalid (nimed)
  [[mang]]   sport, algus, kodu, voorad, kanal, url (kanali saidil), lisatud, markus
  [[koduhall]]  sport, nimi (koduvõistkonna eristavad sõnad), koht (venues.toml nimi): kava rida, millega ühtegi
             mängu ei seostu, lisatakse mänguna selle meeskonna kodumänguna (`unmatched_games`)

    python ulekanded.py   kontrollib faili (väljumiskood 1, kui vigu on)
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import sys
import tomllib
import unicodedata
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit

from scrapers.model import SPORTS, TALLINN, Event

log = logging.getLogger("ulekanded")

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "ulekanded.toml"
LINKS_PATH = ROOT / "data" / "ulekanded.json"
LEARN_DAYS = 180  # nii kaugelt minevikust (arhiivist) õpitakse, kes mida näitab
MATCH_MINUTES = 45  # kava kellaaeg võib mängu algusest nii palju erineda (ülekanne algab varem)
# sõnad, mis võistkondi ei erista (klubi tüüp, ala): nende järgi mängu kava reaga ei seota
_GENERIC = {"vk", "kk", "bc", "fc", "hc", "sk", "bk", "sc", "vc", "jk", "kc", "the", "club", "team", "klubi",
            "spordiklubi", "vorkpalliklubi", "korvpalliklubi", "kasipalliklubi", "jalgpalliklubi", "basket",
            "volley", "volleyball", "basketball", "handball"}

# ülekande tüüp (lehel oma ikoon ja tekst): kanali `tuup` ([[kanal]]) või peetud mängul järelvaatamine
TYPES = {
    "tv": {"title": "Teleülekanne", "button": "Teleülekanne"},        # ERR (ETV, ETV2)
    "veeb": {"title": "Otseülekanne", "button": "Otseülekanne"},      # internetis: Delfi TV, Postimees, YouTube
    "jarel": {"title": "Järelvaatamine", "button": "Vaata järele"},  # peetud mäng
}
CHANNEL_TYPES = ("tv", "veeb")


def watch_kind(video_by: str, past: bool, channel_types: dict[str, str]) -> str:
    """Mängu ülekande tüüp: peetud mäng → "jarel", muidu kanali tüüp ("tv" või vaikimisi "veeb")."""
    if past:
        return "jarel"
    kind = channel_types.get(video_by, "veeb")
    return kind if kind in CHANNEL_TYPES else "veeb"


# sotsiaalmeedia ei ole allikas ega link (VISION.md); YouTube on videoplatvorm, mitte sotsiaalmeedia voog
BANNED_HOSTS = ("facebook.com", "fb.com", "instagram.com", "tiktok.com", "x.com", "twitter.com")


def parse(text: str) -> dict:
    return tomllib.loads(text)


def load(path: Path = DEFAULT_PATH) -> dict:
    path = Path(path)
    return parse(path.read_text(encoding="utf-8")) if path.exists() else {}


def validate(cfg: dict) -> list[str]:
    """Vead failis (tühi loend = korras)."""
    errors: list[str] = []
    names: set[str] = set()
    for i, k in enumerate(cfg.get("kanal", []), 1):
        name, url = k.get("nimi", "").strip(), k.get("url", "")
        if not name:
            errors.append(f"kanal {i}: nimi puudub")
            continue
        if name in names:
            errors.append(f"kanal {name}: topelt")
        names.add(name)
        if url and not url.startswith("https://"):
            errors.append(f"kanal {name}: url peab algama https://")
        if any(h in url for h in BANNED_HOSTS):
            errors.append(f"kanal {name}: sotsiaalmeedia link pole lubatud")
        if k.get("tuup", "veeb") not in CHANNEL_TYPES:
            errors.append(f"kanal {name}: tuup peab olema {' või '.join(CHANNEL_TYPES)}")
        kava = k.get("kava", "")
        if kava and not re.fullmatch(r"[a-z0-9_]+", kava):
            errors.append(f"kanal {name}: kava peab olema adapteri nimi (scrapers/kava_<nimi>.py)")
    registry = {k.get("nimi", "").strip(): k for k in cfg.get("kanal", [])}
    for i, m in enumerate(cfg.get("mang", []), 1):
        label = f"mang {i} ({m.get('kodu', '?')} – {m.get('voorad', '')})"
        if m.get("sport") not in SPORTS:
            errors.append(f"{label}: tundmatu ala")
        if not isinstance(m.get("algus"), datetime):
            errors.append(f"{label}: algus peab olema kuupäev ja kellaaeg (nt 2026-12-05T18:00:00)")
        if not str(m.get("kodu", "")).strip():
            errors.append(f"{label}: kodu puudub")
        kanal = registry.get(m.get("kanal", ""))
        if kanal is None:
            errors.append(f"{label}: kanal {m.get('kanal')!r} pole [[kanal]] nimekirjas")
        elif not domain_ok(str(m.get("url", "")), kanal):
            errors.append(f"{label}: url peab olema https ja kanali {kanal['nimi']!r} saidil")
    for i, h in enumerate(cfg.get("koduhall", []), 1):
        label = f"koduhall {i} ({h.get('nimi', '?')})"
        if h.get("sport") not in SPORTS:
            errors.append(f"{label}: tundmatu ala")
        if not _tokens(h.get("nimi", "")):
            errors.append(f"{label}: nimi puudub või koosneb ainult üldsõnadest")
        if not str(h.get("koht", "")).strip():
            errors.append(f"{label}: koht puudub")
    for i, entry in enumerate(cfg.get("liiga", []), 1):
        label = f"liiga {i} ({entry.get('sport', '?')})"
        if entry.get("sport") not in SPORTS:
            errors.append(f"{label}: tundmatu ala")
        if not entry.get("liigad") and not entry.get("liiga_algus"):
            errors.append(f"{label}: liigad või liiga_algus puudub")
        if not entry.get("kanalid"):
            errors.append(f"{label}: kanalid puudub")
        for name in entry.get("kanalid", []):
            if name not in names:
                errors.append(f"{label}: kanal {name!r} pole [[kanal]] nimekirjas")
    return errors


_YOUTUBE = ("youtube.com", "youtu.be")


def _site(host: str) -> str:
    """Saidi domeen: kaks viimast osa (sport.postimees.ee → postimees.ee)."""
    return ".".join(host.lower().split(".")[-2:])


def domain_ok(url: str, kanal: dict) -> bool:
    """Mängu link peab olema kanali saidil (YouTube'il youtube.com / youtu.be), https ja mitte sotsiaalmeedia."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or any(h in url for h in BANNED_HOSTS):
        return False
    if kanal.get("url"):
        return _site(parts.hostname) == _site(urlsplit(kanal["url"]).hostname or "")
    return kanal.get("nimi") == "YouTube" and _site(parts.hostname) in _YOUTUBE


def manual_streams(cfg: dict) -> list[dict]:
    """Käsitsi (otsinguagendi) lisatud ülekanded [[mang]] samal kujul nagu kava read (vt match)."""
    out = []
    for m in cfg.get("mang", []):
        if not isinstance(m.get("algus"), datetime):
            continue
        start = m["algus"] if m["algus"].tzinfo else m["algus"].replace(tzinfo=TALLINN)
        out.append({"start": start.astimezone(TALLINN), "sport": m.get("sport", ""), "home": m.get("kodu", ""),
                    "away": m.get("voorad", ""), "url": m.get("url", ""), "by": m.get("kanal", "")})
    return out


def _matches(entry: dict, sport: str, league: str) -> bool:
    if entry.get("sport") != sport:
        return False
    prefix = entry.get("liiga_algus", "")
    return league in entry.get("liigad", []) or bool(prefix and league.startswith(prefix))


def learned(events: Iterable[Event]) -> dict[tuple[str, str], Counter]:
    """Mängudest õpitu: (ala, liiga) → mitu mängu iga ülekandja näitas."""
    counts: dict[tuple[str, str], Counter] = {}
    seen: set[str] = set()
    for e in events:
        if e.video_by and e.id not in seen:  # sama mäng arhiivist ja praegustest andmetest ainult korra
            seen.add(e.id)
            counts.setdefault((e.sport, e.league), Counter())[e.video_by] += 1
    return counts


def league_channels(cfg: dict, events: Iterable[Event]) -> dict[tuple[str, str], list[dict]]:
    """(ala, liiga) → [{"name", "url", "games"}]: käsitsi teadaolevad enne, siis õpitud (enim näidanud ees).

    `games` = mitu mängu süsteem ise nägi (0 = ainult käsitsi teada)."""
    events = list(events)
    registry = {k["nimi"]: k for k in cfg.get("kanal", []) if k.get("nimi")}
    learn = learned(events)
    out: dict[tuple[str, str], list[dict]] = {}
    for sport, league in sorted({(e.sport, e.league) for e in events} | set(learn)):
        counts = learn.get((sport, league), Counter())
        names = [n for entry in cfg.get("liiga", []) if _matches(entry, sport, league) for n in entry.get("kanalid", [])]
        names += [n for n, _ in counts.most_common()]
        channels = [{"name": n, "url": registry.get(n, {}).get("url", ""), "games": counts.get(n, 0)}
                    for n in dict.fromkeys(names)]
        if channels:
            out[(sport, league)] = channels
    return out


# --- Ülekandja kava → mängud ---------------------------------------------------

def _tokens(name: str) -> set[str]:
    """Võistkonna nime eristavad sõnad: väiketähed, diakriitikata (Pärnu → parnu, Jēkabpils → jekabpils)."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", name.lower()) if not unicodedata.combining(c))
    return {w for w in re.split(r"[^a-z0-9]+", plain) if len(w) >= 3 and w not in _GENERIC}


def _stem_hits(a: set[str], b: set[str]) -> int:
    """Mitu sõna hulgast `a` on hulgas `b` sama tüvega (üks algab teisega, vähemalt 4 tähte): käänded
    nagu "Otepää" / "Otepääl" loetakse samaks."""
    return sum(1 for x in a if len(x) >= 4 and any(len(y) >= 4 and (x.startswith(y) or y.startswith(x)) for y in b))


def link_of(e: Event, video: str = "", video_by: str = "") -> dict:
    """Seose kirje data/ulekanded.json jaoks (vaikimisi mängu enda link)."""
    return {"video": video or e.video, "video_by": video_by or e.video_by, "start": e.start.isoformat(),
            "sport": e.sport, "league": e.league}


def _candidates(events: list[Event], s: dict) -> list[tuple]:
    """Kava rea sobivad mängud: [(skoor, -minutid, mäng)], parim ees."""
    sh, sa = _tokens(s["home"]), _tokens(s["away"])
    cands = []
    for e in events:
        if e.sport != s["sport"]:
            continue
        if not s["away"]:  # üritus
            if not (e.start.date() <= s["start"].date() <= e.last_day):
                continue
            # ürituse nimi, sari ja linn: „IBU laskesuusatamise MM“ + „Otepää“ ↔ „Laskesuusatamise MM Otepääl“
            score = _stem_hits(_tokens(f"{e.home} {e.away} {e.league} {e.city}"), sh)
            if score >= 2:
                cands.append((score, 0, e))
            continue
        minutes = abs((e.start - s["start"]).total_seconds()) / 60
        if not (minutes <= MATCH_MINUTES or (e.time_tbc and e.start.date() == s["start"].date())):
            continue
        eh, ea = _tokens(e.home), _tokens(e.away)
        straight = len(sh & eh) * len(sa & ea) and len(sh & eh) + len(sa & ea)
        swapped = len(sh & ea) * len(sa & eh) and len(sh & ea) + len(sa & eh)
        score = max(straight, swapped)
        if score:
            cands.append((score, -minutes, e))
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return cands


def match(events: Iterable[Event], streams: Iterable[dict]) -> dict[str, dict]:
    """Kava read → mängud. Tagastab {mängu id: {"video", "video_by", "start", "sport", "league"}}.

    Pallimäng: sama ala, kellaaeg ±MATCH_MINUTES (kellaajata mängul sama päev) ning mõlema võistkonna
    nimes on kava reaga ühine eristav sõna (kodu/võõras võivad olla vahetuses).
    Üritus (kava real võistkondi pole, away tühi): sama ala, ülekande päev on ürituse päevade sees ja
    ürituse nimes on vähemalt 2 sõna, mis on ka kava rea nimes (käänded lubatud).
    Kui kaks mängu sobivad võrdselt hästi, jäetakse rida vahele (parem ilma lingita kui vale link)."""
    events = list(events)
    out: dict[str, dict] = {}
    for s in streams:
        cands = _candidates(events, s)
        if not cands:
            continue
        if len(cands) > 1 and cands[0][:2] == cands[1][:2]:
            log.info("%s: kava rida %s – %s sobib mitmele mängule, jätan vahele", s["by"], s["home"], s["away"])
            continue
        e = cands[0][2]
        out[e.id] = link_of(e, s["url"], s["by"])
    return out


KAVA_SOURCE = "kava_mangud"


def unmatched_games(events: Iterable[Event], streams: Iterable[dict], cfg: dict) -> list[Event]:
    """Kava read, mis ei sobi ühegi olemasoleva mänguga, mängudena (ainult Eesti võistkondade kodumängud).

    Kava annab ainult aja, ala ja „Kodu - Võõras“. Saal tuleb [[koduhall]] tabelist (koduvõistkonna nime
    kõik eristavad sõnad peavad kava rea koduvõistkonna nimes olema). Rida, millel pole koduhalli (välismaa
    klubi, tundmatu meeskond), jääb vahele. Rida, mis sobib mitme mänguga, on mõne mänguga seotud: vahele.
    Tase 1, liiga „<Ala> (kava järgi)“; mängul on kohe ülekande link. Ühe päeva kaks rida samale mängule
    (mitu kanalit) liidetakse: alles jääb esimene."""
    from scrapers.model import new_event  # siin, et ulekanded.py importimine ei vajaks mudelit kohe
    events = list(events)
    halls = [(h["sport"], _tokens(h["nimi"]), h["koht"]) for h in cfg.get("koduhall", []) if _tokens(h.get("nimi", ""))]
    out: dict[str, Event] = {}
    for s in streams:
        if not s["away"] or _candidates(events, s):
            continue
        home = _tokens(s["home"])
        venue = next((v for sport, toks, v in halls if sport == s["sport"] and toks <= home), None)
        if venue is None:
            continue
        e = new_event(source=KAVA_SOURCE, sport=s["sport"], league=f"{SPORTS[s['sport']]} (kava järgi)",
                      start=s["start"], home=s["home"], away=s["away"], venue=venue, city="", url=s["url"],
                      level=1, video=s["url"], video_by=s["by"])
        out.setdefault(e.id, e)
    return list(out.values())


def fetch_streams(cfg: dict, fetcher) -> tuple[list[dict], list[dict]]:
    """Kõigi kavaga kanalite read. Tagastab (read, aruanne kanali kaupa build_report.json jaoks).

    Ühe kava viga ei peata ehitust: aruandes status "failed", varasemad seosed jäävad alles."""
    streams: list[dict] = []
    report: list[dict] = []
    for k in cfg.get("kanal", []):
        if not k.get("kava"):
            continue
        entry = {"source": f"kava_{k['kava']}", "channel": k["nimi"], "status": "ok", "fetched": 0, "saved": 0,
                 "error": ""}
        try:
            module = importlib.import_module(f"scrapers.kava_{k['kava']}")
            rows_ = module.fetch(fetcher)
            entry["fetched"] = len(rows_)
            streams.extend(rows_)
        except Exception as exc:  # noqa: BLE001 - kava viga ei tohi ehitust katki teha
            entry["status"] = "failed"
            entry["error"] = f"{type(exc).__name__}: {exc}"
            log.exception("%s ebaõnnestus", entry["source"])
        report.append(entry)
    return streams, report


def load_links(path: Path = LINKS_PATH) -> dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("links", {})
    except ValueError:
        log.warning("%s: vigane fail, alustan tühjalt", path)
        return {}


def save_links(links: dict[str, dict], path: Path = LINKS_PATH) -> None:
    """Kirjutab ainult siis, kui sisu muutus (igapäevast commit'i pole, kui midagi uut ei leitud)."""
    path = Path(path)
    if load_links(path) == links and path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"links": links}, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")


def update_links(old: dict[str, dict], new: dict[str, dict], today: date,
                 refreshed: Iterable[str] = ()) -> dict[str, dict]:
    """Uued seosed vanade peale. Välja lähevad LEARN_DAYS-ist vanemad ning tulevaste päevade seosed
    kanalitelt, mille kava täna loeti (`refreshed`), kui mäng kavast kadus (ülekanne jäi ära)."""
    refreshed = set(refreshed)
    first = today - timedelta(days=LEARN_DAYS)
    out = {}
    for eid, link in {**old, **new}.items():
        day = datetime.fromisoformat(link["start"]).astimezone(TALLINN).date()
        if day < first:
            continue
        if eid not in new and link["video_by"] in refreshed and day > today:
            continue
        out[eid] = link
    return out


def apply(events: Iterable[Event], links: dict[str, dict]) -> list[Event]:
    """Lisab mängudele kava lingi. Allika enda link (nt järelvaatamine) jääb ette."""
    return [replace(e, video=links[e.id]["video"], video_by=links[e.id]["video_by"])
            if not e.video and e.id in links else e for e in events]


def channel_types(cfg: dict) -> dict[str, str]:
    """Kanali nimi → tüüp ("tv" / "veeb")."""
    return {k["nimi"]: k.get("tuup", "veeb") for k in cfg.get("kanal", []) if k.get("nimi")}


def rows(channels: dict[tuple[str, str], list[dict]]) -> list[dict]:
    """„Meist“ lehe nimekiri: ala järjekord nagu SPORTS, liigad tähestikus."""
    order = {s: i for i, s in enumerate(SPORTS)}
    return [{"sport": SPORTS[s], "league": lg, "channels": ch}
            for (s, lg), ch in sorted(channels.items(), key=lambda kv: (order.get(kv[0][0], 99), kv[0][1]))]


def main() -> int:
    errors = validate(load())
    for err in errors:
        print(err)
    if not errors:
        cfg = load()
        print(f"Korras: {len(cfg.get('kanal', []))} kanalit, {len(cfg.get('liiga', []))} liiga kirjet")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
