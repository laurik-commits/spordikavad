"""Praktikumi lisaleht /praktikum/: materjalid allalaadimiseks (ei kuulu spordikalendri juurde).

Allikas on kaust `site/praktikum/`:
  materjalid/…        failid ja (valikuliselt) alamkaustad; igaüks on lehel link. Alamkausta nimi on pealkiri.
  praktikum.toml      valikuline: title, intro ja kirjeldused failide kaupa ([[fail]] nimi = "…", kirjeldus = "…")
Lehte tehakse ainult siis, kui materjalide kaustas on vähemalt üks fail (muidu `/praktikum/` puudub).
Leht on `noindex, nofollow`, sitemapis pole, ei ole kuskilt lingitud ja ei sisalda statistika koodi. See EI ole
juurdepääsu piirang: GitHub Pages on avalik, igaüks, kellel on link, näeb ja laadib faile.
"""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path
from urllib.parse import quote

SLUG = "praktikum"
SKIP = {".gitkeep", ".DS_Store", "Thumbs.db"}


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.1f} MB"


def _natural(name: str) -> list:
    import re
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def collect(src: Path) -> tuple[dict, list[dict]]:
    """(seadistus, sektsioonid): sektsioon = {"title": alamkausta nimi või "", "files": [{"name","href","size","description"}]}."""
    cfg = {}
    if (src / "praktikum.toml").exists():
        cfg = tomllib.loads((src / "praktikum.toml").read_text(encoding="utf-8"))
    desc = {f.get("nimi", ""): f.get("kirjeldus", "") for f in cfg.get("fail", [])}
    root = src / "materjalid"
    sections: list[dict] = []
    if not root.is_dir():
        return cfg, sections

    def files_in(folder: Path, prefix: str) -> list[dict]:
        out = []
        for p in sorted((x for x in folder.iterdir() if x.is_file() and x.name not in SKIP and not x.name.startswith(".")),
                        key=lambda x: _natural(x.name)):
            rel = f"{prefix}{p.name}"
            out.append({"name": p.name, "href": "materjalid/" + "/".join(quote(part) for part in rel.split("/")),
                        "size": human_size(p.stat().st_size), "description": desc.get(rel) or desc.get(p.name, "")})
        return out

    top = files_in(root, "")
    if top:
        sections.append({"title": "", "files": top})
    for d in sorted((x for x in root.iterdir() if x.is_dir() and not x.name.startswith(".")), key=lambda x: _natural(x.name)):
        files = files_in(d, d.name + "/")
        if files:
            sections.append({"title": d.name, "files": files})
    return cfg, sections


def build(src: Path, out: Path, env, common: dict) -> bool:
    """Kirjutab `<out>/praktikum/index.html` ja kopeerib failid. Tagastab True, kui leht tehti."""
    cfg, sections = collect(src)
    if not sections:
        return False
    target = out / SLUG
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src / "materjalid", target / "materjalid", ignore=shutil.ignore_patterns(*SKIP, ".*"), dirs_exist_ok=True)
    (target / "index.html").write_text(
        env.get_template("praktikum.html").render(common, root="../", title=cfg.get("title", "Praktikum"),
                                                  intro=cfg.get("intro", ""), sections=sections),
        encoding="utf-8")
    return True
