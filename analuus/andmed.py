"""Kõik teadaolevad sündmused: `data/` (praegune seis) ja `archive/` (ajalugu, kuni allikas näitas), sama mäng mitmest allikast liidetud."""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dicts(root: Path = ROOT) -> dict[str, dict]:
    """{id: sündmuse sõnastik}. Arhiiv annab ajaloo, `data/` kirjutab viimase seisu üle."""
    events: dict[str, dict] = {}
    for path in sorted(glob.glob(str(root / "archive" / "*" / "*.json"))):
        for eid, rec in json.loads(Path(path).read_text(encoding="utf-8")).items():
            events[eid] = rec["event"]
    for path in sorted(glob.glob(str(root / "data" / "*.json"))):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for e in data.get("events", []) if isinstance(data, dict) else []:
            events[e["id"]] = e
    return events


def load_events(root: Path = ROOT):
    """Event-objektid, allikate järjekorras (config.toml) ja liidetud sama mäng mitmest allikast (`build.dedupe`)."""
    import build
    from scrapers import config
    from scrapers.model import Event

    order = {s["name"]: i for i, s in enumerate(config.load()["source"])}
    events = sorted((Event.from_dict(e) for e in load_dicts(root).values()), key=lambda e: (order.get(e.source, 999), e.start))
    return build.dedupe(events)[0]
