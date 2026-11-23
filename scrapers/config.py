"""config.toml lugemine."""

from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.toml"


def load(path: Path = DEFAULT_PATH) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def user_agent(cfg: dict) -> str:
    http = cfg.get("http", {})
    ua = http.get("user_agent", "elakaasa-bot")
    contact = http.get("contact", "").strip()
    if contact:
        ua = ua[:-1] + f"; {contact})" if ua.endswith(")") else f"{ua} ({contact})"
    return ua


def _in_range(start: str, end: str, day: date) -> bool:
    """Vahemik kujul "MM-DD" (kordub igal aastal, võib üle aastavahetuse) või "YYYY-MM-DD"."""
    if len(start) == 5 and len(end) == 5:
        md = day.strftime("%m-%d")
        return start <= md <= end if start <= end else (md >= start or md <= end)
    return date.fromisoformat(start) <= day <= date.fromisoformat(end)


def in_season(item: dict, day: date, default: dict | None = None) -> bool:
    """Kas `day` on hooaja sees. `item` võib olla allikas või võistlus; kui võistlusel `seasons` puudub,
    kasutatakse allika (`default`) oma."""
    seasons = item.get("seasons") or (default or {}).get("seasons", [])
    return any(_in_range(s, e, day) for s, e in seasons)
