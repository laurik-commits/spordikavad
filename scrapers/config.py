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
    ua = http.get("user_agent", "spordikavad.ee-bot")
    contact = http.get("contact", "").strip()
    if contact:
        ua = ua[:-1] + f"; {contact})" if ua.endswith(")") else f"{ua} ({contact})"
    return ua


def in_season(source: dict, day: date) -> bool:
    for start, end in source.get("seasons", []):
        if date.fromisoformat(start) <= day <= date.fromisoformat(end):
            return True
    return False
