"""Toimumiskohtade tabel `paigad.toml`: **paik** (koht kaardil) = üks või mitu `venues.toml` kohta ühe koordinaadiga.

Miks: üks kompleks on andmetes sageli mitu kohta (nt „Maarjamäe staadion“ ja „Maarjamäe kunstmuruväljak“); kaardil peab olema üks ring.
`venues.toml` jääb nimede ja linnade allikaks (sh aliased = nimevariandid), `paigad.toml` lisab ainult koordinaadid ja seob duplikaadid.

    [[paik]]
    nimi = "Maarjamäe spordikompleks"     # näidatav nimi
    linn = "Tallinn"
    lat = 59.4297
    lon = 24.8350
    tapsus = "tapne"                      # "tapne" = koht leitud, "linn" = ainult linna keskpunkt (kohta ei leitud või koha asemel on linn)
    kohad = ["Maarjamäe staadion", "Maarjamäe kunstmuruväljak"]   # venues.toml nimed (sama paik)
    kontrollitud = true                   # käsitsi kontrollitud kaardil (valikuline)

    python -m analuus.paigad --puudu     # kasutatud kohad, millel paika veel pole
    python -m analuus.paigad --tabel     # paigad mängude arvuga (Markdown)
"""

from __future__ import annotations

import argparse
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "paigad.toml"
EESTI = (57.45, 59.85, 21.7, 28.3)    # lat min/max, lon min/max: kaugemad punktid on vigased
TAPSUS = ("tapne", "linn")


@dataclass(frozen=True)
class Paik:
    nimi: str
    linn: str
    lat: float
    lon: float
    tapsus: str
    kohad: tuple[str, ...]
    kontrollitud: bool = False
    aliased: tuple[str, ...] = field(default=())   # venues.toml nimevariandid (täidetakse laadimisel)


class Paigad:
    def __init__(self, paigad: list[Paik]) -> None:
        self.paigad = paigad
        self._by_venue: dict[str, Paik] = {}
        for p in paigad:
            for k in p.kohad:
                if k in self._by_venue:
                    raise ValueError(f"koht {k!r} on kahes paigas: {self._by_venue[k].nimi!r} ja {p.nimi!r}")
                self._by_venue[k] = p

    @classmethod
    def load(cls, path: Path = PATH, venues_path: Path | None = None) -> "Paigad":
        data = tomllib.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
        aliases = _aliases(venues_path)
        out = []
        for m in data.get("paik", []):
            if m["tapsus"] not in TAPSUS:
                raise ValueError(f"{m['nimi']}: tapsus peab olema {TAPSUS}")
            lat, lon = float(m["lat"]), float(m["lon"])
            if not (EESTI[0] <= lat <= EESTI[1] and EESTI[2] <= lon <= EESTI[3]):
                raise ValueError(f"{m['nimi']}: koordinaadid ({lat}, {lon}) pole Eestis")
            kohad = tuple(m["kohad"])
            al = tuple(sorted({a for k in kohad for a in aliases.get(k, [])}))
            out.append(Paik(m["nimi"], m["linn"], lat, lon, m["tapsus"], kohad, bool(m.get("kontrollitud", False)), al))
        return cls(out)

    def paik_of(self, venue: str) -> Paik | None:
        return self._by_venue.get(venue)

    def puudu(self, events) -> list[tuple[str, str, int]]:
        """Kohad (nimi, linn, mänge), millel paika pole, mängude arvu järgi."""
        c = Counter((e.venue, e.city) for e in events if e.venue and self.paik_of(e.venue) is None)
        return [(v, city, n) for (v, city), n in c.most_common()]

    def tabel(self, events) -> list[dict]:
        """Paigad mängude arvuga (ala kaupa): [{"paik": Paik, "mange": n, "alad": {ala: n}}], tihedamad ees."""
        n: Counter = Counter()
        alad: dict[str, Counter] = defaultdict(Counter)
        for e in events:
            p = self.paik_of(e.venue) if e.venue else None
            if p:
                n[p.nimi] += 1
                alad[p.nimi][e.sport] += 1
        by_name = {p.nimi: p for p in self.paigad}
        return [{"paik": by_name[k], "mange": v, "alad": dict(alad[k])} for k, v in n.most_common()]


def _aliases(venues_path: Path | None) -> dict[str, list[str]]:
    p = venues_path or Path(__file__).resolve().parent.parent / "venues.toml"
    return {v["name"]: v.get("aliases", []) for v in tomllib.loads(Path(p).read_text(encoding="utf-8")).get("venue", [])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--puudu", action="store_true")
    ap.add_argument("--tabel", action="store_true")
    args = ap.parse_args(argv)
    from .andmed import load_events
    evs = load_events()
    pg = Paigad.load()
    if args.puudu:
        for v, city, n in pg.puudu(evs):
            print(f"{n:5}  {v}  [{city}]")
    if args.tabel:
        print("| # | Mänge | Paik | Linn | Täpsus | Alad |\n|---|---|---|---|---|---|")
        for i, r in enumerate(pg.tabel(evs), 1):
            p = r["paik"]
            print(f"| {i} | {r['mange']} | {p.nimi} | {p.linn} | {p.tapsus} | " + ", ".join(f"{k} {v}" for k, v in r["alad"].items()) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
