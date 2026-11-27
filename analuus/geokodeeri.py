"""Toimumiskohtade koordinaadid OpenStreetMapi Nominatimist (tasuta; kasutuspoliitika: kuni 1 päring sekundis, identifitseeriv User-Agent).

    python -m analuus.geokodeeri --puudu              # geokodeerib kohad, millel `paigad.toml`-is veel paika pole, ja kirjutab JSON-i
    python -m analuus.geokodeeri --valja tulemus.json # kuhu tulemus kirjutatakse (vaikimisi stdout)

Tulemus on ettepanek, mitte lõplik tabel: iga koht saab kandidaadi, mille kaugus linna keskpunktist ei ületa piiri; muidu langeb tagasi
linna keskpunkti (`tapsus = "linn"`). Tippkohad kontrollitakse käsitsi enne `paigad.toml`-i kirjutamist. Päringute tulemusi hoitakse lokaalselt (`--vahemalu`),
nii et sama koht ei tule teist korda.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

URL = "https://nominatim.openstreetmap.org/search?{q}"
UA = "elakaasa-bot/0.1 (+https://elakaasa.ee/; info@elakaasa.ee)"
PAUS = 1.1          # sekundit päringute vahel (Nominatimi kasutuspoliitika)
RAADIUS_KM = 12.0   # kandidaat peab olema nii lähedal linna keskpunktile
RAADIUS_VALD_KM = 25.0
HEAD = {"leisure", "sport", "building", "amenity", "tourism", "man_made", "highway"}
_last = [0.0]


def kaugus_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def paring(q: str, limit: int = 4) -> list[dict]:
    wait = PAUS - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    url = URL.format(q=urllib.parse.urlencode({"q": q, "format": "jsonv2", "limit": limit, "countrycodes": "ee", "accept-language": "et"}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for katse in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                _last[0] = time.monotonic()
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 - üksik võrguviga ei tohi kogu jooksu katkestada
            time.sleep(3 * (katse + 1))
    _last[0] = time.monotonic()
    return []


def linna_keskpunkt(city: str, vahemalu: dict) -> tuple[float, float] | None:
    key = f"linn|{city}"
    if key not in vahemalu:
        res = paring(f"{city}, Eesti", 3)
        vahemalu[key] = (float(res[0]["lat"]), float(res[0]["lon"])) if res else None
    return tuple(vahemalu[key]) if vahemalu[key] else None


GENERIC = {"kunstmuruväljak", "kunstmurustaadion", "jalgpallihall", "jalgpallistaadion", "spordikompleksi", "spordikompleks", "muruväljak",
           "harjutusväljak", "spordiväljak", "jalgpallipark", "staadioni", "staadion", "spordihoone", "spordihall", "spordikeskus", "sh",
           "kool", "kooli", "põhikooli", "gümnaasiumi", "keskkooli", "linna", "valla", "arena", "hall", "ja"}


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).replace("-", " ").split())


def tuum(nimi: str, city: str) -> list[str]:
    """Nime tuumsõnad: ilma üldsõnadeta (staadion, kunstmuruväljak …) ja linnanimeta."""
    skip = {_norm(w) for w in GENERIC} | set(_norm(city).split())
    return [t for t in _norm(nimi).split() if t not in skip and len(t) > 2]


def variandid(nimi: str, city: str) -> list[str]:
    """Päringuvariandid: täisnimi, tuumsõnad koos tüüpsõnaga (staadion, spordikeskus, jalgpallihall)."""
    out = [f"{nimi}, {city}", nimi]
    core = " ".join(t for t in nimi.split() if _norm(t) in set(tuum(nimi, city)) or _norm(t) not in {_norm(w) for w in GENERIC})
    base = core or nimi
    out += [f"{base}, {city}"] + [f"{base} {t}, {city}" for t in ("staadion", "spordikeskus", "jalgpallihall", "spordihoone", "kunstmuruväljak")]
    seen, res = set(), []
    for q in out:
        if q not in seen:
            seen.add(q)
            res.append(q)
    return res


def sobib(c: dict, nimi: str, city: str) -> bool:
    """Kandidaadi `name` peab sisaldama vähemalt ühe nime tuumsõna (muidu on tõenäoliselt lähedal asuv muu rajatis)."""
    core = tuum(nimi, city)
    return not core or any(t in _norm(c.get("name") or "") for t in core)


def geokodeeri(nimi: str, city: str, vahemalu: dict) -> dict:
    """{"lat","lon","tapsus": "tapne" | "linn", "osm": "...", "paring": "...", "kaugus_km": ...} või tapsus "puudub"."""
    kesk = linna_keskpunkt(city, vahemalu)
    vald = "vald" in city.lower()
    piir = RAADIUS_VALD_KM if vald else RAADIUS_KM
    if kesk is None:
        return {"tapsus": "puudub", "paring": "", "osm": "linna keskpunkti ei leitud"}
    if nimi == city or "täpsustamisel" in nimi:
        return {"lat": kesk[0], "lon": kesk[1], "tapsus": "linn", "osm": f"{city} keskpunkt", "paring": city, "kaugus_km": 0.0}
    for q in variandid(nimi, city):
        key = f"koht|{q}"
        if key not in vahemalu:
            vahemalu[key] = paring(q)
        kand = []
        for c in vahemalu[key]:
            p = (float(c["lat"]), float(c["lon"]))
            d = kaugus_km(p, kesk)
            if d <= piir and sobib(c, nimi, city):
                kand.append((0 if c.get("category") in HEAD else 1, d, c))
        if kand:
            _, d, c = sorted(kand, key=lambda x: (x[0], x[1]))[0]
            return {"lat": round(float(c["lat"]), 6), "lon": round(float(c["lon"]), 6), "tapsus": "tapne",
                    "osm": c.get("display_name", "")[:140], "osm_id": f"{c.get('osm_type')}/{c.get('osm_id')}", "paring": q,
                    "kaugus_km": round(d, 1)}
    return {"lat": kesk[0], "lon": kesk[1], "tapsus": "linn", "osm": f"{city} keskpunkt (koha ei leitud)", "paring": nimi, "kaugus_km": 0.0}


def kasutatud_kohad() -> list[tuple[str, str, int]]:
    from .andmed import load_events
    c = Counter((e.venue, e.city) for e in load_events() if e.venue)
    return [(v, city, n) for (v, city), n in c.most_common()]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--valja")
    p.add_argument("--vahemalu", default=str(Path(__file__).with_name("geokood_vahemalu.json")))
    p.add_argument("--kohad", nargs="*", help="ainult need kohad (nimi); vaikimisi kõik kasutatud, mis `paigad.toml`-is puuduvad")
    args = p.parse_args(argv)
    vahemalu = json.loads(Path(args.vahemalu).read_text(encoding="utf-8")) if Path(args.vahemalu).exists() else {}
    from .paigad import Paigad
    paigad = Paigad.load()
    kohad = [(v, c, n) for v, c, n in kasutatud_kohad() if (not args.kohad or v in args.kohad) and (args.kohad or paigad.paik_of(v) is None)]
    out = {}
    for i, (v, city, n) in enumerate(kohad, 1):
        out[v] = dict(geokodeeri(v, city, vahemalu), linn=city, mange=n)
        print(f"{i}/{len(kohad)} {v} [{city}] → {out[v]['tapsus']}", file=sys.stderr)
        Path(args.vahemalu).write_text(json.dumps(vahemalu, ensure_ascii=False), encoding="utf-8")
    text = json.dumps(out, ensure_ascii=False, indent=1)
    if args.valja:
        Path(args.valja).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
