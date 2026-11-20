"""Kogub andmed kõigist allikatest ja genereerib staatilise lehe kausta dist/.

Kasutus:
    python build.py            # kogub andmed ja ehitab lehe
    python build.py --offline  # ainult ehitab lehe data/ kausta viimastest andmetest
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import logging
import shutil
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scrapers import config as cfgmod
from scrapers.http import Fetcher
from scrapers.model import SPORTS, TALLINN, Event
from scrapers.venues import Venues

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
DIST = ROOT / "dist"
REPORT = ROOT / "build_report.json"

log = logging.getLogger("build")

WEEKDAYS = ["esmaspäev", "teisipäev", "kolmapäev", "neljapäev", "reede", "laupäev", "pühapäev"]
SHORT_WEEKDAYS = ["E", "T", "K", "N", "R", "L", "P"]
MONTHS = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli",
          "august", "september", "oktoober", "november", "detsember"]


# --- Kogumine ---------------------------------------------------------------

def _data_file(name: str) -> Path:
    return DATA / f"{name}.json"


def load_saved(name: str) -> list[Event]:
    path = _data_file(name)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Event.from_dict(d) for d in raw["events"]]


def save(name: str, events: list[Event]) -> None:
    DATA.mkdir(exist_ok=True)
    payload = {
        "updated": datetime.now(TALLINN).isoformat(timespec="seconds"),
        "events": [e.to_dict() for e in sorted(events, key=lambda e: (e.start, e.id))],
    }
    _data_file(name).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def only_tallinn(events: list[Event], venues: Venues) -> list[Event]:
    out = []
    for e in events:
        v = venues.lookup(e.venue)
        if v is not None and v.city == "Tallinn":
            out.append(replace(e, venue=v.name, city=v.city))
    return out


def collect(cfg: dict, venues: Venues, fetcher: Fetcher | None, today: date) -> tuple[list[Event], list[dict]]:
    """Tagastab kõik Tallinna mängud ja aruande iga allika kohta.

    Ühe allika viga ei peata ehitust: siis kasutatakse selle allika viimaseid salvestatud andmeid.
    """
    all_events: list[Event] = []
    report: list[dict] = []
    for src in cfg.get("source", []):
        name = src["name"]
        if not src.get("enabled", True):
            continue
        entry = {"source": name, "status": "ok", "fetched": 0, "tallinn": 0, "error": ""}
        events: list[Event] | None = None
        if fetcher is None:
            entry["status"] = "offline"
        else:
            try:
                module = importlib.import_module(f"scrapers.{name}")
            except ModuleNotFoundError:
                entry["status"] = "no_adapter"
                module = None
            if module is not None:
                try:
                    # adapter, mis vajab config.toml-i rida (nt võistluste nimekirja), saab selle kaasa
                    wants_source = "source" in inspect.signature(module.fetch).parameters
                    fetched = module.fetch(fetcher, source=src) if wants_source else module.fetch(fetcher)
                    entry["fetched"] = len(fetched)
                    if not fetched and cfgmod.in_season(src, today):
                        entry["status"] = "empty"
                        entry["error"] = "Hooaja sees 0 mängu"
                    else:
                        events = only_tallinn(fetched, venues)
                        save(name, events)
                except Exception as exc:  # noqa: BLE001 - ükski adapter ei tohi ehitust katki teha
                    entry["status"] = "failed"
                    entry["error"] = f"{type(exc).__name__}: {exc}"
                    log.exception("%s ebaõnnestus", name)
        if events is None:
            events = load_saved(name)
            if entry["status"] in ("failed", "empty"):
                log.warning("%s: kasutan viimaseid salvestatud andmeid (%d mängu)", name, len(events))
        entry["tallinn"] = len(events)
        all_events.extend(events)
        report.append(entry)
    return all_events, report


# --- Genereerimine ----------------------------------------------------------

def et_date(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]}"


def render(events: list[Event], cfg: dict, today: date, out: Path = DIST) -> int:
    site_cfg = cfg.get("site", {})
    days_ahead = int(site_cfg.get("days_ahead", 14))
    base_url = site_cfg.get("base_url", "").rstrip("/") + "/"
    days = [today + timedelta(days=i) for i in range(days_ahead + 1)]

    by_day: dict[date, list[Event]] = {d: [] for d in days}
    for e in events:
        d = e.start.date()
        if d in by_day:
            by_day[d].append(e)
    for lst in by_day.values():
        lst.sort(key=lambda e: (e.time_tbc, e.start, e.sport, e.home))

    present = sorted({e.sport for lst in by_day.values() for e in lst}, key=list(SPORTS).index)
    filters = [{"key": s, "label": SPORTS[s]} for s in present]
    links = [{"sport": l["sport"], "label": SPORTS[l["sport"]], "url": l["url"],
              "note": l.get("note", ""), "link_text": l.get("link_text", "")} for l in cfg.get("external_link", [])]

    env = Environment(loader=FileSystemLoader(SITE), autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["et_date"] = et_date
    tpl = env.get_template("day.html")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for asset in ("style.css", "app.js"):
        shutil.copy(SITE / asset, out / asset)

    day_list = [{"date": d, "label": et_date(d), "short": SHORT_WEEKDAYS[d.weekday()], "count": len(by_day[d])}
                for d in days]
    common = dict(
        sports=SPORTS, filters=filters, links=links, days=day_list, today=today,
        analytics_enabled=site_cfg.get("analytics_enabled", False),
        analytics_token=site_cfg.get("analytics_token", ""), base_url=base_url,
        contact_url=site_cfg.get("contact_url", ""),
    )

    def next_with_games(i: int) -> date | None:
        return next((d for d in days[i + 1:] if by_day[d]), None)

    for i, d in enumerate(days):
        ctx = dict(
            common, day=d, events=by_day[d],
            prev_day=days[i - 1] if i > 0 else None,
            next_day=days[i + 1] if i + 1 < len(days) else None,
            next_games=next_with_games(i),
        )
        page_dir = out / d.isoformat()
        page_dir.mkdir()
        (page_dir / "index.html").write_text(
            tpl.render(ctx, root="../", canonical=f"{base_url}{d.isoformat()}/"), encoding="utf-8")
        if i == 0:
            (out / "index.html").write_text(tpl.render(ctx, root="", canonical=base_url), encoding="utf-8")

    upcoming = sorted((e for e in events if e.start.date() >= today), key=lambda e: (e.start, e.id))
    (out / "events.json").write_text(
        json.dumps({"generated": datetime.now(TALLINN).isoformat(timespec="seconds"),
                    "events": [e.to_dict() for e in upcoming]}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    urls = [base_url] + [f"{base_url}{d.isoformat()}/" for d in days]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{u}</loc><lastmod>{today.isoformat()}</lastmod></url>" for u in urls]
    sitemap.append("</urlset>")
    (out / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return len(days)


# --- Käivitamine ------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="ära tee võrgupäringuid")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    cfg = cfgmod.load()
    venues = Venues.load()
    today = datetime.now(TALLINN).date()
    http = cfg.get("http", {})
    fetcher = None if args.offline else Fetcher(
        cfgmod.user_agent(cfg), delay=http.get("delay", 3.0), host_delays=http.get("host_delays", {}),
        timeout=http.get("timeout", 20.0), retries=http.get("retries", 3))

    events, report = collect(cfg, venues, fetcher, today)
    pages = render(events, cfg, today)
    REPORT.write_text(json.dumps({"date": today.isoformat(), "sources": report,
                                  "unknown_venues": sorted(venues.unknown)}, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    log.info("Kokkuvõte (%s):", today.isoformat())
    for r in report:
        extra = f" – {r['error']}" if r["error"] else ""
        log.info("  %-26s %-10s allikas %4d, Tallinnas %3d%s", r["source"], r["status"], r["fetched"], r["tallinn"], extra)
    if venues.unknown:
        log.info("  Tundmatud toimumiskohad: %s", ", ".join(sorted(venues.unknown)))
    log.info("  Lehti: %d, mänge kokku: %d", pages, len(events))
    return 0


if __name__ == "__main__":
    sys.exit(main())
