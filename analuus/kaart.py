"""Kaardi andmed ja halli mõju analüüs. Ehitus (`build.py`) kutsub `ehita`, mis kirjutab `kaart/andmed.json` ja lehe `kaart/index.html`.

Andmed (kompaktselt, et JSON jääks väikeseks): paigad (`paigad.toml`), iga mäng reana `[paik, päev, minut, ala, tase]`
(päev = päevi alates 2026-01-01, minut = päeva minutid või -1, kui kellaaeg pole teada) ja tulevaste mängude üksikasjad.
Kaart näitab ainult kalendris olevaid liigasid (sama valik nagu leht: peidetud tase välja jäetud).

Halli mõju: iga paiga kohta, kus on vähemalt `MIN_TULEMUSI` tulemust, kodumeeskonna võitude osakaal, võrreldes ootusega (sama liiga ja hooaja
kõigi mängude kodu võitude keskmine) ja Wilsoni 95% usaldusvahemik. **See pole põhjuslik**: ühe klubi koduhallis peegeldab number klubi tugevust.
"""

from __future__ import annotations

import json
import math
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import lood, tulemus as tul
from .paigad import Paigad

ALGUS = date(2026, 1, 1)
MIN_TULEMUSI = 15


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilsoni usaldusvahemik osakaalule k/n (protsentides)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - h) / d, 100 * (c + h) / d)


def halli_moju(events, paigad: Paigad, min_tulemusi: int = MIN_TULEMUSI) -> list[dict]:
    """[{"paik", "linn", "n", "kodu", "viik", "kylaline", "kodu_pct", "viik_pct", "kylaline_pct", "oodatav_pct", "vahe_pp", "lo", "hi",
    "kodumeeskondi", "alad", "oluline"}], kõige rohkem tulemusi ees. Oodatav = sama liiga ja hooaja kõigi mängude kodu võitude keskmine."""
    mangud = []
    for e in events:
        t = tul.parse(e.sport, e.result) if e.away and e.venue else None
        p = paigad.paik_of(e.venue) if t else None
        if p:
            mangud.append((p, e, t))
    liigas: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])    # (ala, liiga, hooaeg) → [kodu võidud, mänge]
    for p, e, t in mangud:
        k = (e.sport, e.league, lood.hooaeg(e.sport, e.start.date()))
        liigas[k][1] += 1
        liigas[k][0] += tul.voitja(t) == "kodu"
    by: dict[str, list] = defaultdict(list)
    for p, e, t in mangud:
        by[p.nimi].append((e, t))
    out = []
    pmap = {p.nimi: p for p in paigad.paigad}
    for nimi, rows in by.items():
        n = len(rows)
        if n < min_tulemusi:
            continue
        voidud = sum(tul.voitja(t) == "kodu" for _, t in rows)
        viigid = sum(tul.voitja(t) == "viik" for _, t in rows)
        oodatav = sum(liigas[(e.sport, e.league, lood.hooaeg(e.sport, e.start.date()))][0] /
                      liigas[(e.sport, e.league, lood.hooaeg(e.sport, e.start.date()))][1] for e, _ in rows) / n * 100
        lo, hi = wilson(voidud, n)
        pct = 100 * voidud / n
        out.append({"paik": nimi, "linn": pmap[nimi].linn, "n": n, "kodu": voidud, "viik": viigid, "kylaline": n - voidud - viigid,
                    "kodu_pct": round(pct, 1), "viik_pct": round(100 * viigid / n, 1), "kylaline_pct": round(100 * (n - voidud - viigid) / n, 1),
                    "oodatav_pct": round(oodatav, 1), "vahe_pp": round(pct - oodatav, 1), "lo": round(lo, 1), "hi": round(hi, 1),
                    "kodumeeskondi": len({e.home for e, _ in rows}), "alad": sorted({e.sport for e, _ in rows}),
                    "oluline": not (lo <= oodatav <= hi)})
    return sorted(out, key=lambda x: (-x["n"], x["paik"]))


def koosta(events, paigad: Paigad, today: date, peidetud_tasemed=(3,)) -> dict:
    """Kaardi JSON: paigad, alad, mängud (reana), tulevased mängud ja halli mõju."""
    from scrapers.model import SPORTS, EVENT_SPORTS
    ev = [e for e in events if e.venue and e.level not in peidetud_tasemed and paigad.paik_of(e.venue)]
    kasutatud = [s for s in SPORTS if any(e.sport == s for e in ev)]
    from scrapers import sports as reg
    ala_idx = {s: i for i, s in enumerate(kasutatud)}
    nimed = sorted({paigad.paik_of(e.venue).nimi for e in ev})
    paik_idx = {n: i for i, n in enumerate(nimed)}
    pmap = {p.nimi: p for p in paigad.paigad}
    hm = {x["paik"]: x for x in halli_moju([e for e in events if e.level not in peidetud_tasemed], paigad)}
    kohad = []
    for n in nimed:
        p = pmap[n]
        h = hm.get(n)
        kohad.append({"n": p.nimi, "l": p.linn, "la": p.lat, "lo": p.lon, "t": p.tapsus,
                      **({"hv": [h["n"], h["kodu_pct"], h["oodatav_pct"], h["kodumeeskondi"]]} if h else {})})
    mangud, tulevased = [], []
    for e in sorted(ev, key=lambda e: (e.start, e.id)):
        d = (e.start.date() - ALGUS).days
        m = -1 if e.time_tbc else e.start.hour * 60 + e.start.minute
        pi = paik_idx[paigad.paik_of(e.venue).nimi]
        mangud.append([pi, d, m, ala_idx[e.sport], e.level])
        if e.start.date() >= today:
            tulevased.append({"p": pi, "d": d, "m": m, "s": ala_idx[e.sport], "l": e.level, "id": e.id,
                              "t": f"{e.home} – {e.away}" if e.away else e.home, "lg": e.league})
    return {"loodud": today.isoformat(), "alg": ALGUS.isoformat(), "kohad": kohad,
            "alad": [{"k": s, "n": SPORTS[s], "c": reg.COLORS[s], "ev": s in EVENT_SPORTS} for s in kasutatud],
            "mangud": mangud, "tulevased": tulevased}


def ehita(out: Path, env, common: dict, events, today: date, base_url: str, urls: list[str], paigad: Paigad | None = None) -> bool:
    """Kirjutab `<out>/kaart/andmed.json` ja `<out>/kaart/index.html`. Tagastab False, kui `paigad.toml` puudub (kaarti ei tehta)."""
    paigad = paigad or Paigad.load()
    if not paigad.paigad:
        return False
    data = koosta(events, paigad, today)
    kaust = out / "kaart"
    kaust.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__).resolve().parent.parent / "site" / "kaart.js", kaust / "kaart.js")
    (kaust / "andmed.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    moju = [x for x in halli_moju([e for e in events if e.level not in (3,)], paigad)][:30]
    (kaust / "index.html").write_text(
        env.get_template("kaart.html").render(common, root="../", canonical=f"{base_url}kaart/", moju=moju, min_tulemusi=MIN_TULEMUSI,
                                              paiku=len(data["kohad"]), mange=len(data["mangud"]), alad=data["alad"]),
        encoding="utf-8")
    urls.append(f"{base_url}kaart/")
    return True
