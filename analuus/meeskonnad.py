"""Meeskonnanimede ühtlustus. Sama meeskond on eri allikates kirjutatud eri moodi („Barrus/Võru VK“, „BARRUS/Võru VK“, „Barrus Võru VK“).

1. Automaatselt: nimed, mis erinevad ainult suur-/väiketähtede, kirjavahemärkide ja täpitähtede poolest, on üks meeskond
   (näidatakse sagedaseimat kirjapilti).
2. Käsitsi: `meeskonnad.toml` (`[[meeskond]] sport, nimi, aliased = [...]`) seob ka erinevad nimed (nt „Valmiera“ ja „Valmiera Glass VIA“).
Noorte- ja teise võistkonna nimed (U-20, II) on tahtlikult eraldi meeskonnad.

    python -m analuus.meeskonnad    # loetleb veel ühtlustamata sarnased nimed ülevaatuseks
"""

from __future__ import annotations

import difflib
import re
import tomllib
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "meeskonnad.toml"


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


class Teams:
    def __init__(self, aliases: dict[tuple[str, str], str] | None = None) -> None:
        self.aliases = aliases or {}          # (ala, norm(nimi)) → kanooniline nimi
        self.display: dict[tuple[str, str], str] = {}   # (ala, võti) → näidatav kirjapilt

    @classmethod
    def load(cls, path: Path = PATH) -> "Teams":
        aliases: dict[tuple[str, str], str] = {}
        if Path(path).exists():
            for m in tomllib.loads(Path(path).read_text(encoding="utf-8")).get("meeskond", []):
                for name in [m["nimi"], *m.get("aliased", [])]:
                    key = (m["sport"], norm(name))
                    if key in aliases and aliases[key] != m["nimi"]:
                        raise ValueError(f"{m['sport']}: {name!r} on kahe meeskonna all ({aliases[key]!r} ja {m['nimi']!r})")
                    aliases[key] = m["nimi"]
        return cls(aliases)

    def fit(self, events) -> "Teams":
        """Valib iga võtme jaoks sagedaseima kirjapildi (aliasega seotud nimed kasutavad `nimi` välja)."""
        seen: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for e in events:
            for t in (e.home, e.away):
                if t:
                    seen[(e.sport, self.key(e.sport, t))][t] += 1
        self.display = {k: c.most_common(1)[0][0] for k, c in seen.items()}
        return self

    def key(self, sport: str, name: str) -> str:
        canon = self.aliases.get((sport, norm(name)))
        return norm(canon) if canon else norm(name)

    def canonical(self, sport: str, name: str) -> str:
        canon = self.aliases.get((sport, norm(name)))
        return canon or self.display.get((sport, norm(name)), name)


def candidates(events, teams: Teams) -> list[tuple[str, str, str]]:
    """Veel ühtlustamata sarnased nimed (ala, a, b) ülevaatuseks: üks nimi sisaldub teises või on väga sarnased."""
    names: dict[str, dict[str, str]] = defaultdict(dict)
    for e in events:
        if not e.away:
            continue   # üritus (etapp, turniir), mitte meeskonnamäng
        for t in (e.home, e.away):
            names[e.sport].setdefault(teams.key(e.sport, t), t)
    out = []
    for sport, by_key in names.items():
        keys = sorted(by_key)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if difflib.SequenceMatcher(None, a, b).ratio() > 0.82 or (len(a) > 4 and (a in b or b in a)):
                    out.append((sport, by_key[a], by_key[b]))
    return out


if __name__ == "__main__":
    from .andmed import load_events
    evs = load_events()
    t = Teams.load().fit(evs)
    for sport, a, b in sorted(candidates(evs, t)):
        print(f"{sport:13} {a!r} ~ {b!r}")
