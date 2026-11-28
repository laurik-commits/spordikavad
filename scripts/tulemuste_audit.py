"""Tulemuste audit: meie salvestatud tulemustest arvutatud liigatabel vs allika enda ametlik tabel (sõltumatu allikas).

    python scripts/tulemuste_audit.py              # jalgpall (jalgpall.ee liigade tabelid; 1 päring liiga kohta, Crawl-Delay 5 s)
    python scripts/tulemuste_audit.py saalijalgpall # saalijalgpall (sama sait, sama tabel)
    python scripts/tulemuste_audit.py vorkpall     # võrkpall (DataProjecti tabelid: mängud, võidud, kaotused, setid)

Iga võistkonna kohta võrreldakse mänge, võite, viike, kaotusi, väravaid ja punkte. Erinevus tähendab kas adapteri viga (nihe, vale suund) või
allika enda otsust, mida tulemused ei näita (tehniline kaotus, punktide mahaarvamine, puuduv mäng): seda tuleb käsitsi vaadata.
"""

from __future__ import annotations

import html
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analuus import tulemus as tul  # noqa: E402
from analuus.andmed import load_dicts  # noqa: E402
from scrapers import config  # noqa: E402
from scrapers.http import Fetcher  # noqa: E402

ROW = re.compile(r"\|\s*(\d+)\|\s*([^|]+?)\s*\|\s*(\d+)\|\s*(\d+)\|\s*(\d+)\|\s*(\d+)\|\s*(\d+):(\d+)\|\s*(-?\d+)")


def tabel_lehelt(page: str) -> dict[str, tuple[int, ...]]:
    """{võistkond: (mänge, võite, viike, kaotusi, väravaid_kodu, väravaid_vastu, punkte)} jalgpall.ee tabeli lehelt (esimene tabel)."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    t = re.sub(r"<[^>]+>", "|", t)
    t = html.unescape(re.sub(r"\s+", " ", t))
    t = re.sub(r"(\| ?)+", "| ", t)
    start = t.find("Võistkond")
    out: dict[str, tuple[int, ...]] = {}
    for m in ROW.finditer(t[start:] if start >= 0 else t):
        name = re.sub(r"^S\. ", "", m.group(2).strip())     # saalijalgpalli tabelis on nimel eesliide „S. “
        if name in out:      # teine tabel (nt grupid): esimene võidab
            break
        out[name] = tuple(int(m.group(i)) for i in (3, 4, 5, 6, 7, 8, 9))
    return out


def arvuta(events: list[dict], liiga: str, sport: str = "jalgpall") -> dict[str, list[int]]:
    """Samad veerud meie tulemustest (jalgpall: võit 3, viik 1)."""
    rows: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])
    for e in events:
        if e["league"] != liiga or not e.get("away"):
            continue
        t = tul.parse(sport, e.get("result", ""))
        if not t:
            continue
        for team, gf, ga in ((e["home"], t.kodu, t.kylaline), (e["away"], t.kylaline, t.kodu)):
            r = rows[team]
            r[0] += 1
            r[1] += gf > ga
            r[2] += gf == ga
            r[3] += gf < ga
            r[4] += gf
            r[5] += ga
            r[6] += 3 * (gf > ga) + (gf == ga)
    return rows


def audit_jalgpall(season: int = 2026, source: str = "jalgpall_ejl", sport: str = "jalgpall") -> int:
    cfg = config.load()
    h = cfg["http"]
    f = Fetcher(h["user_agent"], delay=h.get("delay", 3.0), host_delays=h.get("host_delays", {}))
    src = next(s for s in cfg["source"] if s["name"] == source)
    events = [e for e in load_dicts().values() if e["source"] == source]
    bad = checked = 0
    for comp in src["competitions"]:
        url = f"https://jalgpall.ee/voistlused/{comp['id']}/liigad/table?season={season}"
        try:
            official = tabel_lehelt(f.get(url))
        except Exception as ex:  # noqa: BLE001
            print(f"- {comp['league']}: tabelit ei saanud ({ex})")
            continue
        ours = arvuta(events, comp["league"], sport)
        if not official:
            print(f"- {comp['league']}: allika tabelit ei õnnestunud lugeda")
            continue
        puudu, vaartus, klapib = [], [], 0
        for team, o in official.items():
            m = ours.get(team)
            n = m[0] if m else 0
            if (m is not None and tuple(m) == o) or (m is None and o[0] == 0):
                klapib += 1
            elif n < o[0]:
                puudu.append((team, o, tuple(m) if m else None))      # meil vähem mänge: tehnilised tulemused / allikas ei näita skoori
            else:
                vaartus.append((team, o, tuple(m) if m else None))    # sama arv mänge, aga erinev: võimalik adapteri viga (nihe, vale suund)
        checked += len(official)
        bad += len(vaartus)
        print(f"- {comp['league']}: {len(official)} võistkonda, täpselt klapib {klapib}, meil vähem mänge {len(puudu)}, SAMA MÄNGUDE ARVUGA ERINEB {len(vaartus)}")
        for team, o, m in vaartus:
            print(f"    SUSPEKTNE {team}: allikas {o}, meil {m}   (mänge, V, X, K, väravad, vastu, punkte)")
        for team, o, m in puudu:
            print(f"    vähem mänge {team}: allikas {o}, meil {m}")
    print(f"KOKKU: {checked} võistkonda, sama mängude arvuga erinevaid (suspektne): {bad}")
    return bad


def tabel_dataproject(page: str) -> dict[str, tuple[int, ...]]:
    """{võistkond: (mänge, võite, kaotusi, setti võidetud, setti kaotatud)} DataProjecti tabeli lehelt (esimene tabel)."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    t = re.sub(r"<[^>]+>", "|", t)
    t = html.unescape(re.sub(r"\s+", " ", t))
    t = re.sub(r"(\| ?)+", "| ", t)
    end = t.find("Home Team")
    out: dict[str, tuple[int, ...]] = {}
    for m in re.finditer(r"\| ([^|\d][^|]*?)\| (\d+)\| (\d+)\| (\d+)\| (\d+)\| (\d+)\| (\d+)\| (\d+)\| (\d+)\|", t[: end if end > 0 else len(t)]):
        out.setdefault(m.group(1).strip(), tuple(int(m.group(i)) for i in (3, 4, 5, 6, 7)))
    return out


def arvuta_vorkpall(events: list[dict], liiga: str) -> dict[str, list[int]]:
    rows: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    for e in events:
        if e["league"] != liiga or not e.get("away"):
            continue
        t = tul.parse("vorkpall", e.get("result", ""))
        if not t:
            continue
        for team, sw, sl in ((e["home"], t.kodu, t.kylaline), (e["away"], t.kylaline, t.kodu)):
            r = rows[team]
            r[0] += 1
            r[1] += sw > sl
            r[2] += sw < sl
            r[3] += sw
            r[4] += sl
    return rows


def audit_vorkpall() -> int:
    cfg = config.load()
    h = cfg["http"]
    f = Fetcher(h["user_agent"], delay=h.get("delay", 3.0), host_delays=h.get("host_delays", {}))
    src = next(s for s in cfg["source"] if s["name"] == "vorkpall_dataproject")
    events = [e for e in load_dicts().values() if e["source"] == "vorkpall_dataproject"]
    bad = checked = 0
    for comp in src["competitions"]:
        url = f"https://{comp['host']}.dataproject.com/CompetitionStandings.aspx?ID={comp['id']}" + (f"&PID={comp['pid']}" if comp.get("pid") else "")
        try:
            official = tabel_dataproject(f.get(url))
        except Exception as ex:  # noqa: BLE001
            print(f"- {comp['league']}: tabelit ei saanud ({ex})")
            continue
        ours = arvuta_vorkpall(events, comp["league"])
        if not official:
            print(f"- {comp['league']}: allika tabelit ei õnnestunud lugeda")
            continue
        klapib, puudu, vaartus = 0, [], []
        for team, o in official.items():
            m = ours.get(team)
            n = m[0] if m else 0
            if (m is not None and tuple(m) == o) or (m is None and o[0] == 0):
                klapib += 1
            elif n < o[0]:
                puudu.append((team, o, tuple(m) if m else None))
            else:
                vaartus.append((team, o, tuple(m) if m else None))
        checked += len(official)
        bad += len(vaartus) + len(puudu)
        print(f"- {comp['league']}: {len(official)} võistkonda, täpselt klapib {klapib}, meil vähem mänge {len(puudu)}, ERINEB {len(vaartus)}")
        for team, o, m in vaartus + puudu:
            print(f"    {team}: allikas {o}, meil {m}   (mänge, V, K, setid võidetud, kaotatud)")
    print(f"KOKKU: {checked} võistkonda, mitteklappivaid {bad}")
    return bad


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "jalgpall"
    if which == "vorkpall":
        bad = audit_vorkpall()
    elif which == "saalijalgpall":
        bad = audit_jalgpall(source="saalijalgpall_ejl", sport="saalijalgpall")
    else:
        bad = audit_jalgpall()
    sys.exit(1 if bad else 0)
