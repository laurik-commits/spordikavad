"""Alade register: loeb sports.toml-i ja annab sellest tuletatud sõnastikud.

Üks ala = üks [[sport]] plokk failis sports.toml. Siit tulevad SPORTS ja EVENT_SPORTS (model.py), käänded, menüürühmad,
allikate lingid ja käsitsi kaetud märkused (build.py), Delfi/ERR kava ala tuvastus ning lehe värvid ja nimed:
`css_block()` ja `js_block()` täidavad site/style.css ja site/kalender.js markerite vahe (build.py kopeerib failid
väljundisse nii).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "sports.toml"
_KEY = re.compile(r"[a-z]+")
_COLOR = re.compile(r"#[0-9a-f]{6}")
_REQUIRED = ("key", "name", "gen", "in", "color")
_KNOWN = _REQUIRED + ("group", "gpos", "event", "block", "delfi", "go3", "err", "sources", "manual")


def parse(text: str) -> dict:
    """Register kontrollituna: {"sports": [...], "groups": [...]}. Viskab ValueError, kui midagi on valesti."""
    data = tomllib.loads(text)
    groups, sports = data.get("group", []), data.get("sport", [])
    group_keys = [g["key"] for g in groups]
    seen: set[str] = set()
    for s in sports:
        label = s.get("key", "?")
        for f in _REQUIRED:
            if not str(s.get(f, "")).strip():
                raise ValueError(f"ala {label}: puudub {f!r}")
        extra = set(s) - set(_KNOWN)
        if extra:
            raise ValueError(f"ala {label}: tundmatu väli {sorted(extra)}")
        if not _KEY.fullmatch(s["key"]) or s["key"] in seen:
            raise ValueError(f"ala {label}: võti peab olema väiketähed ja unikaalne")
        seen.add(s["key"])
        if not _COLOR.fullmatch(s["color"]):
            raise ValueError(f"ala {label}: värv peab olema #rrggbb")
        if s.get("group") and s["group"] not in group_keys:
            raise ValueError(f"ala {label}: tundmatu rühm {s['group']!r}")
        if s.get("err"):
            re.compile(s["err"])
        for src in s.get("sources", []):
            if not (src.get("name") and str(src.get("url", "")).startswith("https://")):
                raise ValueError(f"ala {label}: allikal peab olema name ja https url")
    return {"sports": sports, "groups": groups}


def load(path: Path = PATH) -> dict:
    return parse(Path(path).read_text(encoding="utf-8"))


_REG = load()
SPORT_LIST = _REG["sports"]
SPORTS = {s["key"]: s["name"] for s in SPORT_LIST}
EVENT_SPORTS = {s["key"] for s in SPORT_LIST if s.get("event")}
COLORS = {s["key"]: s["color"] for s in SPORT_LIST}
GEN = {s["key"]: s["gen"] for s in SPORT_LIST}
IN = {s["key"]: s["in"] for s in SPORT_LIST}
BLOCK = {s["key"]: s["block"] for s in SPORT_LIST if s.get("block")}
SOURCE_SITES = {s["key"]: [(x["name"], x["url"]) for x in s["sources"]] for s in SPORT_LIST if s.get("sources")}
MANUAL_COVERAGE = {s["key"]: s["manual"] for s in SPORT_LIST if s.get("manual")}
DELFI_LABELS = {label: s["key"] for s in SPORT_LIST for label in s.get("delfi", [])}
GO3_GENRES = {g: s["key"] for s in SPORT_LIST for g in s.get("go3", [])}
ERR_PATTERNS = [(s["err"], s["key"]) for s in SPORT_LIST if s.get("err")]


def groups() -> list[dict]:
    """Menüürühmad: [{"key", "name", "word", "sports": [...]}]; alad rühmas gpos järgi, muidu faili järjekorras."""
    out = []
    for g in _REG["groups"]:
        members = [(s.get("gpos", i), i, s["key"]) for i, s in enumerate(SPORT_LIST) if s.get("group") == g["key"]]
        out.append({"key": g["key"], "name": g["name"], "word": g["word"], "sports": [k for _, _, k in sorted(members)]})
    return out


def css_block() -> str:
    """Alade värvid ja klassid style.css jaoks (:root muutujad on eraldi, vt css_vars)."""
    lines = [f".s-border-{k} {{ border-left-color: var(--{k}); }}" for k in SPORTS]
    return "\n".join(lines)


def css_vars() -> str:
    return "\n".join(f"  --{s['key']}: {s['color']};" for s in SPORT_LIST)


def css_fill() -> str:
    return "\n".join(f".s-{k} {{ background: var(--{k}); }}" for k in SPORTS)


def js_block() -> str:
    names = ", ".join(f'{k}: "{v}"' for k, v in SPORTS.items())
    blocks = ", ".join(f'{k}: "{v}"' for k, v in BLOCK.items())
    return f"  var SPORTS = {{{names}}};\n  var BLOCK = {{{blocks}}};"


MARK = re.compile(r"(/\* @sports:(\w+) \*/\n)(.*?)(\n?/\* @sports:end \*/)", re.S)


def fill(text: str) -> str:
    """Asendab markerite `/* @sports:<nimi> */ … /* @sports:end */` vahe registrist genereeritud sisuga."""
    parts = {"vars": css_vars, "border": css_block, "fill": css_fill, "js": js_block}

    def repl(m: re.Match) -> str:
        if m.group(2) not in parts:
            raise ValueError(f"tundmatu marker {m.group(2)!r}")
        return f"{m.group(1)}{parts[m.group(2)]()}\n/* @sports:end */"
    return MARK.sub(repl, text)
