"""Avab, uuendab või sulgeb GitHub Issue'sid build_report.json põhjal.

- Allikas ebaõnnestus, andis hooaja sees 0 tulevast mängu või mõni võistlus jäi tühjaks
  → avatakse issue (üks allika kohta). Allikas töötab jälle → issue suletakse kommentaariga.
- Tundmatud toimumiskohad ja lähipäevade mängud ilma toimumiskohata → kaks ühist issue't.
  Kui nimekiri muutub, uuendatakse issue sisu ja lisatakse kommentaar (sellest tuleb e-kiri).
  Kui nimekiri on tühi, suletakse issue.

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
NO_VENUE_TITLE = "Mängud ilma toimumiskohata"
BROKEN = ("failed", "empty", "partial")


def title_for(source: str) -> str:
    return f"Allikas katki: {source}"


def _list_body(intro: str, items: list[str]) -> str:
    return intro + "\n\n" + "\n".join(f"- {i}" for i in items)


def plan(report: dict, open_issues: dict[str, str] | set[str]
         ) -> tuple[list[tuple[str, str]], list[str], list[tuple[str, str]]]:
    """Tagastab (avatavad [(pealkiri, sisu)], suletavad [pealkiri], uuendatavad [(pealkiri, uus sisu)]).

    open_issues: avatud issue'd {pealkiri: sisu} (või ainult pealkirjade hulk).
    """
    bodies = open_issues if isinstance(open_issues, dict) else {t: "" for t in open_issues}
    to_open: list[tuple[str, str]] = []
    to_close: list[str] = []
    to_update: list[tuple[str, str]] = []

    for src in report.get("sources", []):
        title = title_for(src["source"])
        broken = src["status"] in BROKEN
        if broken and title not in bodies:
            fallback = ("Lehel kasutatakse viimaseid salvestatud andmeid"
                        if src["status"] != "partial" else "Ülejäänud võistlused uuenevad tavapäraselt")
            body = (
                f"Automaatne teade ({report.get('date')}).\n\n"
                f"- Allikas: `{src['source']}`\n"
                f"- Olek: `{src['status']}`\n"
                f"- Viga: {src.get('error') or '–'}\n"
                f"- {fallback} ({src.get('saved', 0)} mängu).\n\n"
                "Tõenäoline põhjus: allika leht muutus või uuel hooajal on võistluse ID uus "
                "(`config.toml` → `competitions`). Vaata Actions'i logi ja SOURCES.md. "
                "Issue suletakse ise, kui allikas jälle töötab."
            )
            to_open.append((title, body))
        elif not broken and src["status"] == "ok" and title in bodies:
            to_close.append(title)

    collective = [
        (VENUE_TITLE, report.get("unknown_venues", []),
         "Need toimumiskohad puuduvad failist `venues.toml`. Lisa need õige linnaga, muidu nende mänge ei kuvata:"),
        (NO_VENUE_TITLE, [g for s in report.get("sources", []) for g in s.get("no_venue", [])],
         "Neil lähipäevade mängudel pole allikas toimumiskohta märgitud, seega neid lehel ei kuvata. "
         "Tavaliselt lisab liit koha hiljem ise. Kui see ei juhtu, kontrolli adapterit:"),
    ]
    for title, items, intro in collective:
        if not items:
            if title in bodies:
                to_close.append(title)
            continue
        body = _list_body(intro, sorted(items))
        if title not in bodies:
            to_open.append((title, body))
        elif bodies[title].strip() != body.strip():
            to_update.append((title, body))
    return to_open, to_close, to_update


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
        open_issues = json.loads(gh("issue", "list", "--label", LABEL, "--state", "open",
                                    "--json", "number,title,body"))
    numbers = {i["title"]: i["number"] for i in open_issues}
    bodies = {i["title"]: i.get("body", "") for i in open_issues}

    to_open, to_close, to_update = plan(report, bodies)
    for title, body in to_open:
        print(f"Avan: {title}")
        if not args.dry_run:
            gh("issue", "create", "--title", title, "--body", body, "--label", LABEL)
    for title, body in to_update:
        print(f"Uuendan: {title}")
        if not args.dry_run:
            gh("issue", "edit", str(numbers[title]), "--body", body)
            gh("issue", "comment", str(numbers[title]), "--body", f"Nimekiri muutus ({report.get('date')}).")
    for title in to_close:
        print(f"Sulgen: {title}")
        if not args.dry_run:
            msg = {VENUE_TITLE: "Kõik toimumiskohad on nüüd teada",
                   NO_VENUE_TITLE: "Kõigil lähipäevade mängudel on nüüd toimumiskoht"}.get(title, "Allikas töötab jälle")
            gh("issue", "close", str(numbers[title]), "--comment", f"{msg} ({report.get('date')}).")
    if not (to_open or to_close or to_update):
        print("Muudatusi pole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
