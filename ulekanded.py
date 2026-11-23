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
   olemas. Kava ridu ei lisata mängudena.

ulekanded.toml:
  [[kanal]]  ülekandja nimi (sama, mis `video_by`), leht, kuhu link viib, ja valikuliselt kava (adapter)
  [[liiga]]  sport + liigad (täpsed nimed) või liiga_algus (nimi algab nii, nt koondised) + kanalid (nimed)

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
        kava = k.get("kava", "")
        if kava and not re.fullmatch(r"[a-z0-9_]+", kava):
            errors.append(f"kanal {name}: kava peab olema adapteri nimi (scrapers/kava_<nimi>.py)")
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


def match(events: Iterable[Event], streams: Iterable[dict]) -> dict[str, dict]:
    """Kava read → mängud. Tagastab {mängu id: {"video", "video_by", "start", "sport", "league"}}.

    Sama mäng = sama ala, kellaaeg ±MATCH_MINUTES (kellaajata mängul sama päev) ning mõlema võistkonna
    nimes on kava reaga ühine eristav sõna (kodu/võõras võivad olla vahetuses). Kui kaks mängu sobivad
    võrdselt hästi, jäetakse rida vahele (parem ilma lingita kui vale link)."""
    events = list(events)
    out: dict[str, dict] = {}
    for s in streams:
        sh, sa = _tokens(s["home"]), _tokens(s["away"])
        cands = []
        for e in events:
            if e.sport != s["sport"]:
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
        if not cands:
            continue
        cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
        if len(cands) > 1 and cands[0][:2] == cands[1][:2]:
            log.info("%s: kava rida %s – %s sobib mitmele mängule, jätan vahele", s["by"], s["home"], s["away"])
            continue
        e = cands[0][2]
        out[e.id] = {"video": s["url"], "video_by": s["by"], "start": e.start.isoformat(),
                     "sport": e.sport, "league": e.league}
    return out


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
