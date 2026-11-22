"""Korvpall: Bigbank/Kalevi mängud klubi kodulehelt (bckalev.ee/ajakava/).

Korvpalliliidu lehed (basket.ee, estlatbl.com) keelavad robotid, seega liiga teiste klubide mänge siin pole.
bckalev.ee robots.txt lubab /ajakava/ lehe (keelatud on ainult admin, WooCommerce'i add-to-cart ja
?kategooria= / ?srch= parameetrid), crawl-delay'd pole.

Leht on WordPressi SportPressi tabel. Kõik mängud on ühes HTML-is (lehekülgedeks jagab neid brauser, `data-sp-rows`),
seega piisab ühest päringust. Rea kuju:
  <td class="data-date" itemprop="startDate" content="2026-11-21T19:00+02:00"><a href="…/event/…/">…</a></td>
  <td class="data-event">…<a>  A vs B</a></td>
  <td class="data-league">Eesti-Läti Korvpalliliiga</td>
  <td class="data-venue"><div itemprop="address">Saal</div></td>
"A vs B" on kodu vs võõrsil (kontrollitud: Keila KK vs Kalev Keilas, BC Pärnu vs Kalev Pärnus).
Tühi väli ja "Asukoht selgumisel" tähendavad, et saali pole (venue = "").
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime

from .http import FetchError
from .model import TALLINN, Event, new_event, parse_score

log = logging.getLogger(__name__)

NAME = "korvpall_kalev"
SPORT = "korvpall"
URL = "https://bckalev.ee/ajakava/"
RESULTS_URL = "https://bckalev.ee/tulemused/"  # sama tabel + tulemuste veerg; ka robots.txt lubab

_ROW = re.compile(r'<tr class="sp-row[^"]*"[^>]*>(.*?)</tr>', re.S)
_START = re.compile(r'<td class="data-date"[^>]*\bcontent="([^"]+)"[^>]*>\s*<a href="([^"]+)"', re.S)
_CELL = {k: re.compile(rf'<td class="data-{k}"[^>]*>(.*?)</td>', re.S) for k in ("event", "league", "venue")}
_RESULTS = re.compile(r'<td class="data-results"[^>]*>(.*?)</td>', re.S)  # ainult tulemuste lehel: "83 - 81" või "-"
_TAGS = re.compile(r"<[^>]+>")
_VS = re.compile(r"\s+vs\.?\s+", re.I)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def _venue(value: str) -> str:
    return "" if not value or "selgumisel" in value.lower() else value


def parse(page: str) -> list[Event]:
    events: list[Event] = []
    for row in _ROW.findall(page):
        start, cells = _START.search(row), {k: rx.search(row) for k, rx in _CELL.items()}
        if not start or not all(cells.values()):
            continue
        teams = _VS.split(_text(cells["event"].group(1)), maxsplit=1)
        if len(teams) != 2:
            log.warning("korvpall_kalev: ei saa võistkondi eraldada: %r", cells["event"].group(1)[:80])
            continue
        res = _RESULTS.search(row)
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=_text(cells["league"].group(1)),
                start=datetime.fromisoformat(start.group(1)),
                home=teams[0], away=teams[1],
                venue=_venue(_text(cells["venue"].group(1))), city="", url=start.group(2),
                result=parse_score(_text(res.group(1))) if res else "",
            )
        )
    return events


def season_start(today: date) -> date:
    """Hooaeg algab augustis: tulemuste leht sisaldab ka vanemaid hooaegu, neid ei võeta."""
    return date(today.year if today.month >= 8 else today.year - 1, 8, 1)


def fetch(fetcher, today: date | None = None) -> list[Event]:
    """Ajakava (tulevased mängud) ja tulemuste leht (mängitud mängud selle hooaja algusest)."""
    today = today or datetime.now(TALLINN).date()
    events = parse(fetcher.get(URL))
    try:
        first = season_start(today)
        events += [e for e in parse(fetcher.get(RESULTS_URL)) if e.result and e.start.date() >= first]
    except FetchError as exc:  # tulemused on lisa: ajakava peab ka ilma nendeta töötama
        log.warning("%s: tulemuste lehte ei saanud: %s", NAME, exc)
    return events
