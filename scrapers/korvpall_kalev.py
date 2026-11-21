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
from datetime import datetime

from .model import Event, new_event

log = logging.getLogger(__name__)

NAME = "korvpall_kalev"
SPORT = "korvpall"
URL = "https://bckalev.ee/ajakava/"

_ROW = re.compile(r'<tr class="sp-row[^"]*"[^>]*>(.*?)</tr>', re.S)
_START = re.compile(r'<td class="data-date"[^>]*\bcontent="([^"]+)"[^>]*>\s*<a href="([^"]+)"', re.S)
_CELL = {k: re.compile(rf'<td class="data-{k}"[^>]*>(.*?)</td>', re.S) for k in ("event", "league", "venue")}
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
        events.append(
            new_event(
                source=NAME, sport=SPORT, league=_text(cells["league"].group(1)),
                start=datetime.fromisoformat(start.group(1)),
                home=teams[0], away=teams[1],
                venue=_venue(_text(cells["venue"].group(1))), city="", url=start.group(2),
            )
        )
    return events


def fetch(fetcher) -> list[Event]:
    return parse(fetcher.get(URL))
