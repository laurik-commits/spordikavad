"""Otsingu agendi pull request'i automaatse merge'i kontroll (töövoog „Automaatne merge“).

Käivitatakse ALATI main haru koodiga. PR-i failid loetakse andmetena (`git show <sha>:<fail>`),
PR-i koodi ei käivitata, seega ei saa PR kontrolli ennast muuta. PR merge'itakse ainult siis,
kui KÕIK kontrollid läbivad, muidu jääb see omanikule üle vaatamiseks.

Kontrollikihid:
1. Muudetud failid: ainult kasitsi.toml, venues.toml, config.toml ja allikad.toml.
2. config.toml: muutuda tohivad ainult uued kohad [geo.place] all (olemasoleva maakonnaga).
3. venues.toml: olemasolevad saalid muutmata, uusi kuni MAX_NEW_VENUES, linn on Eestis.
4. kasitsi.toml: fail on korrektne (scrapers.kasitsi); olemasolevaid kirjeid ei muudeta; eemaldada
   võib ainult üle 30 päeva vanu; uusi 1..MAX_NEW_EVENTS; algus tänasest kuni MAX_DAYS_AHEAD päeva;
   `added` viimase 3 päeva sees; `note` (hinnang) olemas; saal on teada ja Eestis.
5. Iga uue kirje allikas: robots.txt lubab, leht vastab ja lehel on mängu kuupäev ning
   võistkonna või ürituse nimi.
6. allikad.toml (allikate register): fail on korrektne (allikad.check); kirjeid ei kustutata;
   olemasolevatel kirjetel tohib muuta ainult välju kontrollitud, markus, kuju, robots, kandidaat
   (ja kasutuse "keelatud"-ks); uusi kuni MAX_NEW_SOURCES, nende kasutus on agent, vihje või keelatud
   (adapterit saab märkida ainult omanik). Registri muudatus ei muuda lehte, seega allikat ei avata.

Kasutus (GitHub Actions):  python scripts/automerge_check.py --head <sha> --out result.md
Väljumiskood 0 = võib merge'ida, 1 = jääb omanikule. result.md läheb PR-i kommentaariks.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import allikad  # noqa: E402
from scrapers import config as cfgmod  # noqa: E402
from scrapers import kasitsi  # noqa: E402
from scrapers.geo import Geo  # noqa: E402
from scrapers.model import TALLINN, Event  # noqa: E402
from scrapers.venues import Venues  # noqa: E402

ALLOWED_FILES = {"kasitsi.toml", "venues.toml", "config.toml", "allikad.toml"}
MAX_NEW_SOURCES = 15
SOURCE_EDITABLE = {"kontrollitud", "markus", "kuju", "robots", "kandidaat"}
MAX_NEW_EVENTS = 10
MAX_NEW_VENUES = 5
MAX_DAYS_AHEAD = 60
KEEP_DAYS = 30        # nii vanu kirjeid võib eemaldada
ADDED_SLACK = 3       # `added` võib olla kuni 3 päeva tagasi
MAX_PAGE = 3_000_000  # baiti

MONTHS_ET = ["jaanuar", "veebruar", "marts", "aprill", "mai", "juuni", "juuli",
             "august", "septemb", "oktoob", "novemb", "detsemb"]
MONTHS_EN = ["january", "february", "march", "april", "may", "june", "july",
             "august", "september", "october", "november", "december"]


# --- 1-3: failid, config.toml, venues.toml ------------------------------------

def check_files(changed: list[str]) -> list[str]:
    if not changed:
        return ["PR ei muuda ühtegi faili"]
    other = sorted(set(changed) - ALLOWED_FILES)
    return [f"muudetud on fail, mida automaatselt ei merge'ita: {', '.join(other)}"] if other else []


def check_config(base: str, head: str) -> list[str]:
    if base == head:
        return []
    b, h = tomllib.loads(base), tomllib.loads(head)
    b_places = b.get("geo", {}).get("place", {})
    h_places = h.get("geo", {}).get("place", {})
    problems = []
    for name, county in b_places.items():
        if h_places.get(name) != county:
            problems.append(f"config.toml: olemasolev koht {name!r} muutus või kadus")
    counties = b.get("geo", {}).get("county", {})
    for name in sorted(set(h_places) - set(b_places)):
        if h_places[name] not in counties:
            problems.append(f"config.toml: uue koha {name!r} maakond {h_places[name]!r} pole olemas")

    def without_places(cfg: dict) -> dict:
        cfg = dict(cfg)
        geo = dict(cfg.get("geo", {}))
        geo.pop("place", None)
        cfg["geo"] = geo
        return cfg

    if without_places(b) != without_places(h):
        problems.append("config.toml: muutunud on midagi muud peale [geo.place] uute kohtade")
    return problems


def _venue_items(text: str) -> list[dict]:
    return tomllib.loads(text).get("venue", [])


def check_venues(base: str, head: str, geo: Geo) -> list[str]:
    if base == head:
        return []
    b, h = _venue_items(base), _venue_items(head)
    problems = []
    for item in b:
        if item not in h:
            problems.append(f"venues.toml: olemasolev saal {item.get('name')!r} muutus või kadus")
    new = [item for item in h if item not in b]
    if len(new) > MAX_NEW_VENUES:
        problems.append(f"venues.toml: uusi saale {len(new)} (lubatud kuni {MAX_NEW_VENUES})")
    for item in new:
        if not geo.is_estonian(item.get("city", "")):
            problems.append(f"venues.toml: uue saali {item.get('name')!r} linn {item.get('city')!r} pole Eestis")
    try:
        Venues.from_text(head)
    except (ValueError, KeyError) as exc:
        problems.append(f"venues.toml ei ole korrektne: {exc}")
    return problems


# --- 6: allikad.toml -----------------------------------------------------------

def check_sources(base: str, head: str) -> tuple[list[str], bool]:
    """Tagastab (probleemid, kas registris muutus midagi)."""
    if base == head:
        return [], False
    try:
        b, h = allikad.parse(base) if base else [], allikad.parse(head)
    except ValueError as exc:  # tomllib.TOMLDecodeError on ValueError
        return [f"allikad.toml ei ole korrektne TOML: {exc}"], True
    problems = [f"allikad.toml: {e}" for e in allikad.check(h)]
    key = lambda it: str(it.get("url", "")).rstrip("/").lower()  # noqa: E731
    hb = {key(it): it for it in h}
    for old in b:
        new = hb.get(key(old))
        if new is None:
            problems.append(f"allikad.toml: kirje on eemaldatud või selle url muutus: {old.get('nimi')}")
            continue
        changed = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
        if new.get("kasutus") == "keelatud" and old.get("kasutus") in ("agent", "vihje"):
            changed.discard("kasutus")
        bad = sorted(changed - SOURCE_EDITABLE)
        if bad:
            problems.append(f"allikad.toml: kirjel {old.get('nimi')!r} on muudetud välju, mida agent "
                            f"muuta ei tohi: {', '.join(bad)}")
    bkeys = {key(it) for it in b}
    added = [it for it in h if key(it) not in bkeys]
    if len(added) > MAX_NEW_SOURCES:
        problems.append(f"allikad.toml: uusi allikaid {len(added)} (lubatud kuni {MAX_NEW_SOURCES})")
    for it in added:
        if it.get("kasutus") not in ("agent", "vihje", "keelatud"):
            problems.append(f"allikad.toml: uue allika {it.get('nimi')!r} kasutus peab olema agent, vihje "
                            "või keelatud (adapterit märgib omanik)")
    return problems, True


# --- 4: kasitsi.toml -----------------------------------------------------------

def _raw_by_id(text: str, events: list[Event]) -> dict[str, dict]:
    """Sündmuse id → selle toores TOML-kirje (et näha `note` ja `added` välju)."""
    raw = tomllib.loads(text).get("event", [])
    return {e.id: item for e, item in zip(events, raw)}


def check_kasitsi(base: str, head: str, today: date, venues: Venues, geo: Geo
                  ) -> tuple[list[str], list[Event]]:
    """Tagastab (probleemid, uued kirjed)."""
    try:
        head_events = kasitsi.parse(head)
    except ValueError as exc:
        return [str(exc)], []
    try:
        base_events = kasitsi.parse(base) if base else []
    except ValueError:
        base_events = []
    problems: list[str] = []
    b = {e.id: e for e in base_events}
    h = {e.id: e for e in head_events}
    raw = _raw_by_id(head, head_events)

    for eid, e in b.items():
        if eid not in h:
            if e.start.date() >= today - timedelta(days=KEEP_DAYS):
                problems.append(f"eemaldatud kirje pole üle {KEEP_DAYS} päeva vana: {kasitsi_title(e)}")
        elif h[eid] != e:
            problems.append(f"olemasolevat kirjet on muudetud: {kasitsi_title(e)}")

    new = [e for eid, e in h.items() if eid not in b]
    if len(new) > MAX_NEW_EVENTS:
        problems.append(f"uusi kirjeid {len(new)} (lubatud kuni {MAX_NEW_EVENTS})")
    for e in new:
        item = raw.get(e.id, {})
        t = kasitsi_title(e)
        if not today <= e.start.date() <= today + timedelta(days=MAX_DAYS_AHEAD):
            problems.append(f"{t}: kuupäev {e.start:%d.%m.%Y} pole tänasest {MAX_DAYS_AHEAD} päeva sees")
        added = item.get("added")
        if isinstance(added, date) and not today - timedelta(days=ADDED_SLACK) <= added <= today:
            problems.append(f"{t}: added = {added} pole viimase {ADDED_SLACK} päeva sees")
        if not str(item.get("note", "")).strip():
            problems.append(f"{t}: puudub note (agendi hinnang allikale)")
        v = venues.lookup(e.venue)
        if v is None:
            problems.append(f"{t}: saal {e.venue!r} puudub venues.toml-ist")
        elif not geo.is_estonian(v.city):
            problems.append(f"{t}: saal {v.name!r} ({v.city}) pole Eestis")
    return problems, new


def kasitsi_title(e: Event) -> str:
    name = f"{e.home} – {e.away}" if e.away else e.home
    return f"{e.start:%d.%m} {name}"


# --- 5: allika kontroll --------------------------------------------------------

def _norm(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("õ", "o"), ("ü", "u"), ("š", "s"), ("ž", "z")):
        text = text.replace(a, b)
    text = re.sub(r"(?<![a-z])([a-z])[-\s](?=\d)", r"\1", text)   # vanuseklass "U-16", "U 16" → "u16"
    return " ".join(text.split())


def date_found(text: str, d: date) -> bool:
    """Kas normaliseeritud tekstis on kuupäev mõnel levinud kujul (5.12, 05.12.2026, 5. detsember, ...)."""
    day, mon = d.day, d.month
    patterns = [
        rf"(?<!\d)0?{day}\.\s?0?{mon}(?!\d)",                  # 5.12 / 05.12.2026 / 5. 12
        rf"(?<!\d)0?{day}/0?{mon}/",                           # 05/12/2026
        re.escape(d.isoformat()),                              # 2026-12-05
        rf"(?<!\d){day}\.?\s+{MONTHS_ET[mon - 1]}",            # 5. detsember(il)
        rf"(?<!\d){day}(st|nd|rd|th)?\s+(of\s+)?{MONTHS_EN[mon - 1][:3]}",  # 5 December / 5th Dec
        rf"{MONTHS_EN[mon - 1][:3]}[a-z]*\.?\s+{day}(?!\d)",   # December 5
    ]
    return any(re.search(p, text) for p in patterns)


def name_found(text: str, name: str) -> bool:
    """Nimi on lehel, kui kõik selle sisukad sõnad (vähemalt 3 tähte) on lehel eraldi sõnadena."""
    words = re.findall(r"\w+", _norm(name))
    words = [w for w in words if len(w) >= 3] or words
    return bool(words) and all(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words)


def page_problems(page: str, e: Event) -> list[str]:
    text = _norm(page)
    problems = []
    if not date_found(text, e.start.date()):
        problems.append(f"lehel pole kuupäeva {e.start:%d.%m.%Y}")
    names = [e.home, e.away] if e.away else [e.home, e.league]
    if not any(name_found(text, n) for n in names):
        problems.append("lehel pole võistkonna ega ürituse nime (" + " / ".join(names) + ")")
    return problems


def http_get(url: str, user_agent: str, timeout: float = 20.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Language": "et,en"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(MAX_PAGE)
            return resp.status, raw.decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc)


def verify_source(e: Event, get, user_agent: str) -> list[str]:
    """get(url) → (olekukood, tekst). Kontrollib robots.txt-i ja lehe sisu."""
    parts = urlsplit(e.url)
    status, robots = get(f"{parts.scheme}://{parts.netloc}/robots.txt")
    if status == 200:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(robots.splitlines())
        if not rp.can_fetch(user_agent, e.url):
            return [f"robots.txt keelab lehe {e.url}"]
    elif status not in (404, 410):
        return [f"robots.txt-i ei saanud kontrollida ({status or robots})"]
    status, page = get(e.url)
    if status != 200:
        return [f"allika leht ei vasta ({status or page}): {e.url}"]
    return [f"{p}: {e.url}" for p in page_problems(page, e)]


# --- Käivitamine ---------------------------------------------------------------

def evaluate(changed: list[str], read_base, read_head, today: date, get, user_agent: str) -> list[str]:
    """read_base/read_head(fail) → faili sisu ("" kui faili pole). Tagastab kõik probleemid."""
    problems = check_files(changed)
    if problems:
        return problems
    head_cfg = read_head("config.toml")
    problems += check_config(read_base("config.toml"), head_cfg)
    geo = Geo(tomllib.loads(head_cfg))
    problems += check_venues(read_base("venues.toml"), read_head("venues.toml"), geo)
    try:
        venues = Venues.from_text(read_head("venues.toml"))
    except (ValueError, KeyError):
        return problems
    kp, new = check_kasitsi(read_base("kasitsi.toml"), read_head("kasitsi.toml"), today, venues, geo)
    problems += kp
    sp, sources_changed = check_sources(read_base("allikad.toml"), read_head("allikad.toml"))
    problems += sp
    if not new and not kp and not sources_changed:
        problems.append("PR-is pole uusi kasitsi.toml kirjeid ega registri muudatusi (ainult saalid või "
                        "eemaldused): vaata üle käsitsi")
    if problems:
        return problems  # allikaid ei koormata, kui PR nagunii omanikule jääb
    for e in new:
        problems += [f"{kasitsi_title(e)}: {p}" for p in verify_source(e, get, user_agent)]
    return problems


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout


def _show(ref: str, path: str) -> str:
    try:
        return _git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", required=True, help="PR-i viimane commit (sha)")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--out", default="result.md")
    args = ap.parse_args(argv)

    merge_base = _git("merge-base", args.base, args.head).strip()
    changed = [p for p in _git("diff", "--name-only", merge_base, args.head).splitlines() if p]
    cfg = cfgmod.load()
    ua = cfgmod.user_agent(cfg)
    today = datetime.now(TALLINN).date()
    problems = evaluate(changed, lambda p: _show(merge_base, p), lambda p: _show(args.head, p),
                        today, lambda url: http_get(url, ua), ua)
    if problems:
        body = ("**Automaatne kontroll: jääb omanikule üle vaatamiseks.**\n\n"
                + "\n".join(f"- {p}" for p in problems)
                + "\n\nKui kõik on korras, merge'i käsitsi. Kontrolli reeglid: `scripts/automerge_check.py`.")
    else:
        body = ("Automaatne kontroll läbis: muudetud ainult lubatud failid, kirjed on korrektsed ja "
                "iga uue mängu allika lehel on kuupäev ning võistkonna või ürituse nimi.")
    Path(args.out).write_text(body + "\n", encoding="utf-8")
    print(body)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
