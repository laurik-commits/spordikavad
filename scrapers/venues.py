"""Toimumiskohtade nimekiri: eri allikate kirjapildid → üks normaliseeritud nimi ja linn."""

from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "venues.toml"


@dataclass(frozen=True)
class Venue:
    name: str
    city: str


def _key(text: str) -> str:
    """Võrdlusvõti: väiketähed, kirjavahemärgid ja liigsed tühikud maha."""
    text = text.lower().replace("ä", "a").replace("ö", "o").replace("õ", "o").replace("ü", "u")
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


class Venues:
    def __init__(self, venues: list[Venue], aliases: dict[str, Venue]) -> None:
        self.venues = venues
        self._index = aliases
        self.unknown: set[str] = set()

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "Venues":
        return cls.from_text(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_text(cls, text: str) -> "Venues":
        data = tomllib.loads(text)
        venues: list[Venue] = []
        index: dict[str, Venue] = {}
        for item in data.get("venue", []):
            v = Venue(name=item["name"], city=item["city"])
            venues.append(v)
            for alias in [item["name"], *item.get("aliases", [])]:
                k = _key(alias)
                if k in index and index[k] != v:
                    raise ValueError(f"Alias {alias!r} on kahe saali all: {index[k].name} ja {v.name}")
                index[k] = v
        return cls(venues, index)

    def lookup(self, raw: str) -> Venue | None:
        """Leiab saali. Tundmatu nimi kirjutatakse logisse ja jäetakse meelde kokkuvõtte jaoks."""
        v = self._index.get(_key(raw))
        if v is None and raw.strip():
            if raw not in self.unknown:
                log.warning("Tundmatu toimumiskoht: %r (lisa venues.toml faili)", raw)
            self.unknown.add(raw)
        return v

    def is_tallinn(self, raw: str) -> bool:
        v = self.lookup(raw)
        return v is not None and v.city == "Tallinn"
