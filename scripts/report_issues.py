"""Avab või sulgeb GitHub Issue'sid build_report.json põhjal.

- Allikas ebaõnnestus või andis hooaja sees 0 mängu → avatakse issue (üks allika kohta).
- Allikas töötab jälle → avatud issue suletakse kommentaariga.
- Tundmatud toimumiskohad → üks ühine issue, mida uuendatakse.

Käivitatakse GitHub Actionsis (vajab `gh` ja GH_TOKEN-it). Kohapeal: --dry-run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "allikas"
VENUE_TITLE = "Tundmatud toimumiskohad"


def title_for(source: str) -> str:
    return f"Allikas katki: {source}"


def plan(report: dict, open_titles: set[str]) -> tuple[list[tuple[str, str]], list[str]]:
    """Tagastab (avatavad [(pealkiri, sisu)], suletavad [pealkiri])."""
    to_open: list[tuple[str, str]] = []
    to_close: list[str] = []
    for src in report.get("sources", []):
        title = title_for(src["source"])
        broken = src["status"] in ("failed", "empty")
        if broken and title not in open_titles:
            body = (
                f"Automaatne teade ({report.get('date')}).\n\n"
                f"- Allikas: `{src['source']}`\n"
                f"- Olek: `{src['status']}`\n"
                f"- Viga: {src.get('error') or '–'}\n"
                f"- Lehel kasutatakse viimaseid salvestatud andmeid ({src.get('saved', 0)} mängu).\n\n"
                "Tõenäoline põhjus: allika leht muutus. Vaata Actions'i logi ja SOURCES.md. "
                "Issue suletakse ise, kui allikas jälle töötab."
            )
            to_open.append((title, body))
        elif not broken and src["status"] == "ok" and title in open_titles:
            to_close.append(title)
    unknown = report.get("unknown_venues", [])
    if unknown and VENUE_TITLE not in open_titles:
        lines = "\n".join(f"- {v}" for v in unknown)
        to_open.append((VENUE_TITLE, f"Need toimumiskohad puuduvad failist `venues.toml`. "
                                     f"Lisa need õige linnaga (Tallinna mängud muidu ei kuvata):\n\n{lines}"))
    return to_open, to_close


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default=str(ROOT / "build_report.json"))
    args = parser.parse_args(argv)

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    if args.dry_run:
        open_issues = []
    else:
        gh("label", "create", LABEL, "--color", "d93f0b", "--description", "Andmeallika probleem", "--force")
        open_issues = json.loads(gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number,title"))
    by_title = {i["title"]: i["number"] for i in open_issues}

    to_open, to_close = plan(report, set(by_title))
    for title, body in to_open:
        print(f"Avan: {title}")
        if not args.dry_run:
            gh("issue", "create", "--title", title, "--body", body, "--label", LABEL)
    for title in to_close:
        print(f"Sulgen: {title}")
        if not args.dry_run:
            gh("issue", "close", str(by_title[title]), "--comment", f"Allikas töötab jälle ({report.get('date')}).")
    if not to_open and not to_close:
        print("Muudatusi pole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
