"""Allikate register (allikad.toml): kust leiab infot Eestis toimuvate spordimängude kohta.

Otsingu agent kasutab seda kontrollnimekirjana (kasutus "agent" ja "vihje") ja lisab uusi allikaid.
Kirjed kasutusega "adapter:<nimi>" loetakse automaatselt (scrapers/<nimi>.py).

    python allikad.py           kokkuvõte liikide kaupa ja vead (väljumiskood 1, kui vigu on)
    python allikad.py --agent   agendi kontrollnimekiri (agent, siis vihje)
"""

from __future__ import annotations

import sys
import tomllib
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from scrapers.model import SPORTS

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "allikad.toml"

KINDS = ("hall", "linn", "liit", "klubi", "rahvusvaheline", "pilet", "uudised")
FORMS = ("html", "js", "api", "pdf")
ROBOTS = ("lubatud", "keelatud", "puudub", "kontrollimata")
REQUIRED = ("nimi", "liik", "url", "alad", "piirkond", "kuju", "robots", "kasutus", "kontrollitud")
OPTIONAL = ("kandidaat", "markus")
# sotsiaalmeedia ei ole allikas (VISION.md)
BANNED_HOSTS = ("facebook.com", "fb.com", "instagram.com", "tiktok.com", "x.com", "twitter.com")


def parse(text: str) -> list[dict]:
    return tomllib.loads(text).get("allikas", [])


def load(path: Path = DEFAULT_PATH) -> list[dict]:
    path = Path(path)
    return parse(path.read_text(encoding="utf-8")) if path.exists() else []


def adapters() -> set[str]:
    return {p.stem for p in (ROOT / "scrapers").glob("*.py") if not p.stem.startswith("_")}


def check(items: list[dict], known_adapters: set[str] | None = None) -> list[str]:
    """Tagastab vead (tühi = korras)."""
    known_adapters = adapters() if known_adapters is None else known_adapters
    errors: list[str] = []
    seen: dict[str, int] = {}
    for n, item in enumerate(items, start=1):
        where = f"kirje {n} ({item.get('nimi', '?')})"
        missing = [k for k in REQUIRED if k not in item or item[k] in ("", None, [])]
        unknown = [k for k in item if k not in REQUIRED + OPTIONAL]
        problems = [f"puudub {k!r}" for k in missing] + [f"tundmatu väli {k!r}" for k in unknown]
        url = str(item.get("url", ""))
        host = (urlsplit(url).hostname or "").lower()
        if url and (not url.startswith("https://") and not url.startswith("http://") or not host):
            problems.append("url peab algama https://")
        if any(host == b or host.endswith("." + b) for b in BANNED_HOSTS):
            problems.append(f"sotsiaalmeedia ({host}) pole allikas")
        key = url.rstrip("/").lower()
        if key in seen:
            problems.append(f"sama url on juba kirjes {seen[key]}")
        seen.setdefault(key, n)
        if item.get("liik") and item["liik"] not in KINDS:
            problems.append(f"tundmatu liik {item['liik']!r} (lubatud: {', '.join(KINDS)})")
        if item.get("kuju") and item["kuju"] not in FORMS:
            problems.append(f"tundmatu kuju {item['kuju']!r} (lubatud: {', '.join(FORMS)})")
        if item.get("robots") and item["robots"] not in ROBOTS:
            problems.append(f"tundmatu robots {item['robots']!r} (lubatud: {', '.join(ROBOTS)})")
        alad = item.get("alad", [])
        if not isinstance(alad, list) or any(a != "kõik" and a not in SPORTS for a in alad):
            problems.append(f"alad peab olema loend: \"kõik\" või {', '.join(SPORTS)}")
        use = str(item.get("kasutus", ""))
        if use and use not in ("agent", "vihje", "keelatud"):
            if not use.startswith("adapter:"):
                problems.append("kasutus peab olema adapter:<nimi>, agent, vihje või keelatud")
            elif use.split(":", 1)[1] not in known_adapters:
                problems.append(f"adapterit {use.split(':', 1)[1]!r} pole kaustas scrapers/")
        if item.get("robots") == "keelatud" and use != "keelatud":
            problems.append("robots.txt keelab, seega kasutus peab olema \"keelatud\"")
        if "kontrollitud" in item and not isinstance(item["kontrollitud"], date):
            problems.append("kontrollitud peab olema kuupäev (2026-11-22)")
        if "kandidaat" in item and not isinstance(item["kandidaat"], bool):
            problems.append("kandidaat peab olema true või false")
        errors += [f"{where}: {p}" for p in problems]
    return errors


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    items = load()
    errors = check(items)
    if "--agent" in argv:
        for use in ("agent", "vihje"):
            print(f"== {use} ==")
            for it in items:
                if it.get("kasutus") == use:
                    note = f"  ({it['markus']})" if it.get("markus") else ""
                    print(f"- [{it['liik']}] {it['nimi']}: {it['url']}{note}")
    else:
        kinds = Counter(it.get("liik") for it in items)
        uses = Counter(str(it.get("kasutus", "")).split(":")[0] for it in items)
        print(f"Allikaid {len(items)}: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
        print("Kasutus: " + ", ".join(f"{k} {v}" for k, v in uses.most_common()))
        cands = [it["nimi"] for it in items if it.get("kandidaat")]
        if cands:
            print("Adapteri kandidaadid: " + ", ".join(cands))
    for e in errors:
        print(f"VIGA: {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
