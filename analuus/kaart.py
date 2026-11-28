"""Kaardi andmed. Ehitus (`build.py`) kutsub `ehita`, mis kirjutab `kaart/andmed.json`, `kaart/tekstid.json` ja lehe `kaart/index.html`.

`andmed.json` (kompaktselt): paigad (`paigad.toml`), linnade keskpunktid, iga mäng reana `[paik, päev, minut, ala, tase, id]`
(päev = päevi alates 2026-01-01, minut = päeva minutid või -1, kui kellaaeg pole teada). `tekstid.json`: iga mängu rea kohta `[pealkiri, liiga]`
samas järjekorras (laetakse eraldi, kaardi esmane kuvamine ei oota seda). Kaart näitab ainult kalendris olevaid liigasid (peidetud tase välja jäetud).
Halli mõju statistikat kaardil ei ole: see tuleb lehele /analuus/ alles pärast ülevaatust (vt `halliefekt.py`).
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from .paigad import Paigad

ALGUS = date(2026, 1, 1)


LINNA_ZUUM = 12


def linnad(paigad: Paigad, cities: list[dict]) -> list[dict]:
    """[{"s": slug, "n": nimi, "la", "lo", "z"}]: linna paikade keskmine koordinaat (kaardi algvaade linnale)."""
    out = []
    for c in cities:
        ps = [p for p in paigad.paigad if p.linn == c["name"]]
        if ps:
            out.append({"s": c["slug"], "n": c["name"], "la": round(sum(p.lat for p in ps) / len(ps), 4),
                        "lo": round(sum(p.lon for p in ps) / len(ps), 4), "z": LINNA_ZUUM})
    return out


def koosta(events, paigad: Paigad, today: date, peidetud_tasemed=(3,), cities: list[dict] | None = None) -> tuple[dict, list]:
    """(kaardi JSON, tekstid): paigad, linnad, alad, mängud (reana, koos id-ga) ja mängude pealkirjad samas järjekorras."""
    from scrapers.model import SPORTS, EVENT_SPORTS
    from scrapers import sports as reg
    ev = [e for e in events if e.venue and e.level not in peidetud_tasemed and paigad.paik_of(e.venue)]
    kasutatud = [s for s in SPORTS if any(e.sport == s for e in ev)]
    ala_idx = {s: i for i, s in enumerate(kasutatud)}
    nimed = sorted({paigad.paik_of(e.venue).nimi for e in ev})
    paik_idx = {n: i for i, n in enumerate(nimed)}
    pmap = {p.nimi: p for p in paigad.paigad}
    kohad = [{"n": pmap[n].nimi, "l": pmap[n].linn, "la": pmap[n].lat, "lo": pmap[n].lon, "t": pmap[n].tapsus} for n in nimed]
    mangud, tekstid = [], []
    for e in sorted(ev, key=lambda e: (e.start, e.id)):
        d = (e.start.date() - ALGUS).days
        m = -1 if e.time_tbc else e.start.hour * 60 + e.start.minute
        mangud.append([paik_idx[paigad.paik_of(e.venue).nimi], d, m, ala_idx[e.sport], e.level, e.id])
        tekstid.append([f"{e.home} – {e.away}" if e.away else e.home, e.league])
    return ({"loodud": today.isoformat(), "alg": ALGUS.isoformat(), "kohad": kohad, "linnad": linnad(paigad, cities or []),
             "alad": [{"k": s, "n": SPORTS[s], "c": reg.COLORS[s], "ev": s in EVENT_SPORTS} for s in kasutatud],
             "mangud": mangud}, tekstid)


def ehita(out: Path, env, common: dict, events, today: date, base_url: str, urls: list[str], paigad: Paigad | None = None,
          cities: list[dict] | None = None) -> bool:
    """Kirjutab `<out>/kaart/` failid. Tagastab False, kui `paigad.toml` puudub (kaarti ei tehta)."""
    paigad = paigad or Paigad.load()
    if not paigad.paigad:
        return False
    data, tekstid = koosta(events, paigad, today, cities=cities)
    kaust = out / "kaart"
    kaust.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__).resolve().parent.parent / "site" / "kaart.js", kaust / "kaart.js")
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))   # noqa: E731
    (kaust / "andmed.json").write_text(dump(data), encoding="utf-8")
    (kaust / "tekstid.json").write_text(dump(tekstid), encoding="utf-8")
    (kaust / "index.html").write_text(
        env.get_template("kaart.html").render(common, root="../", canonical=f"{base_url}kaart/", paiku=len(data["kohad"]),
                                              mange=len(data["mangud"]), alad=data["alad"]),
        encoding="utf-8")
    urls.append(f"{base_url}kaart/")
    return True


def ehita_analuus(out: Path, env, common: dict, base_url: str) -> None:
    """Lehekülg /analuus/: praegu ainult märge „tulekul“ (halli mõju tabel avaldatakse alles pärast ülevaatust). noindex, sitemapis pole."""
    kaust = out / "analuus"
    kaust.mkdir(parents=True, exist_ok=True)
    (kaust / "index.html").write_text(env.get_template("analuus.html").render(common, root="../", canonical=f"{base_url}analuus/"),
                                      encoding="utf-8")
