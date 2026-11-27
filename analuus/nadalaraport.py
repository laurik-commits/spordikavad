"""Nädalaraport: üllatused, seeriad, tasavägised mängud ja rekordid (Markdown ja JSON).

    python -m analuus.nadalaraport                  # viimane täisnädal (esmaspäev–pühapäev) enne tänast päeva
    python -m analuus.nadalaraport --end 2026-11-08 # nädal, mis lõpeb sel pühapäeval
    python -m analuus.nadalaraport --stdout         # ainult Markdown ekraanile, faile ei kirjuta

Väljund: `raportid/<aasta>-W<nädal>.md` ja `.json` (sama nädala raport kirjutatakse üle, seega on käivitamine korduv).
Raport arvutatakse ainult kalendris olevate liigade tulemustest (`data/`, `archive/`); vt `analuus/lood.py`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import lood
from .andmed import ROOT, load_events
from .meeskonnad import Teams

EST_MONTHS = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober", "november", "detsember"]
SPORT_NAMES: dict[str, str] = {}


def nimi(sport: str) -> str:
    if not SPORT_NAMES:
        from scrapers.model import SPORTS
        SPORT_NAMES.update(SPORTS)
    return SPORT_NAMES.get(sport, sport)


def viimane_nadal(today: date) -> tuple[date, date]:
    """Viimane täisnädal: esmaspäev ja pühapäev, mis lõppeb enne `today`."""
    last_sunday = today - timedelta(days=today.weekday() + 1)
    return last_sunday - timedelta(days=6), last_sunday


def koosta(events, teams: Teams, algus: date, lopp: date) -> dict:
    # raport on „nädala lõpu seisuga“: hilisemaid mänge ei arvestata (vanema nädala raport ei tohi tulevikku teada)
    ms = [m for m in lood.mangud(events, teams) if m.paev <= lopp]
    aken = [m for m in ms if algus <= m.paev <= lopp]
    iso = algus.isocalendar()
    ser = lood.seeriad(ms, algus, lopp)
    return {
        "nadal": f"{iso.year}-W{iso.week:02d}", "algus": algus.isoformat(), "lopp": lopp.isoformat(),
        "mange_tulemusega": len(aken), "mange_alade_kaupa": dict(Counter(m.sport for m in aken).most_common()),
        "mange_taseme_kaupa": {lood.TASE[t]: n for t, n in sorted(Counter(m.tase for m in aken).items())},
        "ullatused": lood.ullatused(ms, algus, lopp),
        "seeriad": ser,
        "tasavagised": lood.tasavagised(ms, algus, lopp),
        "rekordid": lood.rekordid(ms, algus, lopp),
        "markused": markused(ms, aken),
    }


def markused(ms, aken) -> list[str]:
    out = ["Raport katab ainult kalendris olevaid liigasid ja ainult alasid, mille tulemused on andmetes (jalgpall, võrkpall, korvpall, käsipall, saalijalgpall, saalihoki, jäähoki)."]
    out.append("Tabelit andmetes pole: üllatused ja seeriad tuginevad tulemustest arvutatud tabelile ja on täpsed ainult siis, kui liiga mängud on andmetes täielikud.")
    out.append("Lisaaeg on teada ainult jäähokis; võrkpallis on teada setid, mitte punktid; viik ainult aladel, kus see on võimalik.")
    small = sorted({m.sport for m in ms if sum(1 for x in ms if x.sport == m.sport) < 30})
    if small:
        out.append("Vähe ajalugu (alla 30 tulemuse, seeriad ja rekordid on esialgsed): " + ", ".join(nimi(s) for s in small) + ".")
    return out


def _paev(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day}. {EST_MONTHS[d.month - 1][:3]}"


def _tase(items: list[dict]):
    main = [x for x in items if x["tase"] in lood.PEAMISED]
    rest = [x for x in items if x["tase"] not in lood.PEAMISED]
    return main, rest


SEERIA_SONA = {"võidud": "võitu järjest", "kaotused": "kaotust järjest", "kaotuseta": "mängu kaotuseta", "võiduta": "mängu võiduta"}


def _rida_ullatus(x: dict) -> str:
    # nimesid ei käänata: „X (10. koht) – Y (6. koht) 3:1, võitis X“
    return (f"- {x['voitja']} ({x['voitja_koht']}. koht) võitis kohtumises {x['kaotaja']} ({x['kaotaja_koht']}. koht) {x['tulemus']}, "
            f"{nimi(x['sport']).lower()}, {x['liiga']} ({x['meeskondi']} meeskonda, {_paev(x['paev'])})")


def _rida_seeria(x: dict) -> str:
    tapne = "" if x.get("usaldusvaarne", True) else " ⚠ andmed võivad olla puudulikud"
    return f"- **{x['meeskond']}**: {x['pikkus']} {SEERIA_SONA[x['tyyp']]}, {nimi(x['sport']).lower()}, {x['liiga']} ({_paev(x['paev'])}){tapne}"


def _rida_katkes(x: dict) -> str:
    return (f"- **{x['meeskond']}**: {x['pikkus']} {SEERIA_SONA[x['tyyp']]} katkes ({x['katkestas']}, {_paev(x['paev'])}), "
            f"{nimi(x['sport']).lower()}, {x['liiga']}")


def _rida_tasa(x: dict) -> str:
    return f"- {x['mang']}, {nimi(x['sport']).lower()}, {x['liiga']} ({x['pohjus']}, {_paev(x['paev'])})"


def _rida_rekord(x: dict) -> str:
    mark = " **UUS**" if x["uus"] else (" (võrdsustas)" if x.get("voordsustas") else "")
    return f"- {nimi(x['sport'])} {x['hooaeg']}: {x['kategooria']} {x['vaartus']} {x['ühik']}: {x['mang']}, {x['liiga']} ({_paev(x['paev'])}){mark}"


def _rekordid_md(rekordid: list[dict]) -> list[str]:
    out = []
    for ulatus, pealkiri in (("tipp", "Tipp- ja esiliigad ning koondised"), ("kõik", "Kõik liigad (sh noored ja madalamad)")):
        rida = [_rida_rekord(x) for x in rekordid if x["ulatus"] == ulatus]
        if rida:
            out += [f"### {pealkiri}"] + rida + [""]
    return out or ["_Rekordeid ei olnud._"]


def markdown(r: dict) -> str:
    a, b = date.fromisoformat(r["algus"]), date.fromisoformat(r["lopp"])
    kuu = f"{a.day}. {EST_MONTHS[a.month - 1]}" if a.month != b.month else f"{a.day}."
    out = [f"# Nädalaraport {r['nadal']} ({kuu}–{b.day}. {EST_MONTHS[b.month - 1]} {b.year})", "",
           f"Tulemusega mänge: **{r['mange_tulemusega']}**"
           + (" (" + ", ".join(f"{nimi(s).lower()} {n}" for s, n in r["mange_alade_kaupa"].items()) + ")" if r["mange_tulemusega"] else "") + ".", ""]

    def sektsioon(title: str, items: list[dict], row, tyhi: str):
        out.append(f"## {title}")
        main, rest = _tase(items)
        if main:
            out.extend(row(x) for x in main)
        else:
            out.append(tyhi if not rest else "_Tipp- ja esiliigades ja koondistes selliseid ei olnud._")
        if rest:
            out.extend(["", f"<details><summary>Noored ja madalamad liigad ({len(rest)})</summary>", ""])
            out.extend(row(x) for x in rest[:30])
            if len(rest) > 30:
                out.append(f"- … ja veel {len(rest) - 30}")
            out.extend(["", "</details>"])
        out.append("")

    sektsioon("Üllatused", r["ullatused"], _rida_ullatus, "_Sel nädalal üllatusi ei olnud._")
    ser = r["seeriad"]
    sektsioon("Seeriad (pikenesid sel nädalal)", ser["jatkub"], _rida_seeria, "_Pikki seeriaid ei olnud._")
    sektsioon("Katkenud seeriad", ser["katkes"], _rida_katkes, "_Pikki seeriaid ei katkenud._")
    sektsioon("Tasavägised mängud", r["tasavagised"], _rida_tasa, "_Tasavägiseid mänge ei olnud._")
    out.append("## Rekordid (hooajal kehtivad)")
    out += _rekordid_md(r["rekordid"])
    out += ["## Märkused"] + [f"- {m}" for m in r["markused"]]
    return "\n".join(out) + "\n"


def kirjuta(r: dict, kaust: Path) -> list[Path]:
    kaust.mkdir(parents=True, exist_ok=True)
    md, js = kaust / f"{r['nadal']}.md", kaust / f"{r['nadal']}.json"
    md.write_text(markdown(r), encoding="utf-8")
    js.write_text(json.dumps(r, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    return [md, js]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--end", help="nädala viimane päev (pühapäev), vaikimisi viimane täisnädal")
    p.add_argument("--stdout", action="store_true")
    p.add_argument("--out", default=str(ROOT / "raportid"))
    args = p.parse_args(argv)
    today = datetime.now(ZoneInfo("Europe/Tallinn")).date()
    if args.end:
        lopp = date.fromisoformat(args.end)
        algus = lopp - timedelta(days=6)
    else:
        algus, lopp = viimane_nadal(today)
    events = load_events()
    r = koosta(events, Teams.load().fit(events), algus, lopp)
    if args.stdout:
        print(markdown(r))
    else:
        for path in kirjuta(r, Path(args.out)):
            print("kirjutatud:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
