"""Motosport: Eesti Mootorrattaspordi Föderatsiooni kalender (msport.ee) iCal-voona.

robots.txt lubab (keelab ainult /wp-admin/ ja WooCommerce'i failid). Kalendriplugin (Modern Events Calendar)
pakub kogu kalendrit ühe iCal-failina: https://msport.ee/?mec-ical-feed=1 (kõik aastad, ~500 üritust).

Iga VEVENT: SUMMARY (nimi), DTSTART/DTEND, URL (ürituse leht), CATEGORIES (ala: Motokross, Enduro, …),
LOCATION harva. Pluginal on ajavööndi viga: terve päeva üritus on kujul DTSTART:20261205T200000Z, mis on
Tallinna aja järgi eelmise päeva õhtu (tegelik päev on 6.12, nagu ürituse lehel). Seetõttu: kohalik kellaaeg
19:00 või hiljem → järgmine päev ilma kellaajata; DTEND on samamoodi "järgmise päeva" kujul (välja arvatud).

Toimumiskoht: LOCATION puudub peaaegu alati, aga koht on tavaliselt nimes ("Kiltsi lennuväli", "Karksi-Nuia").
config.toml-is on märksõnade tabel `venue_hints` (märksõna nimes → koht venues.toml-ist). Ilma kohata üritus
jääb lehelt välja ja lähipäevadel ilmub see aruandesse ("Mängud ilma toimumiskohata"), siis lisa märksõna.
Välismaa etapid (nimes "(LV)", "Riga", "FIN" …, vt `foreign_words`) jäävad välja.

Tase: noored (ENKV, Särtsukad, "noor", "kids") → 4; klubivõistlused → 3 (peidetud); muu → 1.
Välja jäävad koolitused, laagrid, galad, trennipäevad, tühistatud ja edasi lükatud üritused.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from .model import TALLINN, Event, new_event

NAME = "motosport_emf"
SPORT = "motosport"
URL = "https://msport.ee/?mec-ical-feed=1"

SKIP = re.compile(r"koolitus|laager|gala|trennipäev|seminar|koosolek|õppepäev|tühistatud|jääb ära|lükkub edasi"
                  r"|hooaja\s*lõp", re.I)
SKIP_CATEGORIES = {"Koolitus", "EMF üritus", "Hooaja lõpetamine"}
YOUTH = re.compile(r"\bENKV\b|särtsuka|noor|\bkids\b|minimoto", re.I)
CLUB = re.compile(r"klubi", re.I)
DEFAULT_FOREIGN = [r"\(LV\)", r"\bLV\b", r"\bLT\b", r"\bFIN\b", "Läti", "Leedu", "Soome", "Riga", "Rīga",
                   "Latvia", "Lithuania", "Finland", "Sweden"]


def _unfold(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n"))


def _field(block: str, key: str) -> str:
    m = re.search(rf"^{key}(?:;[^:\n]*)?:(.*)$", block, re.M)
    return m.group(1).strip().replace("\\,", ",").replace("\\;", ";") if m else ""


def _when(value: str) -> tuple[datetime, bool]:
    """iCal aeg → (Tallinna aeg, kas terve päev). Vt mooduli kirjeldus (pluginal on ajavööndi viga)."""
    if len(value) == 8:  # VALUE=DATE
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=TALLINN), True
    dt = datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
    dt = dt.replace(tzinfo=timezone.utc).astimezone(TALLINN) if value.endswith("Z") else dt.replace(tzinfo=TALLINN)
    if dt.hour >= 19:
        return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0), True
    if dt.hour < 7:
        return dt.replace(hour=0, minute=0, second=0), True
    return dt, False


def _venue(title: str, location: str, hints: dict[str, str]) -> str:
    for word in sorted(hints, key=len, reverse=True):  # pikem märksõna enne ("SuperCross Tallinn" vs "Tallinn")
        if word.lower() in title.lower():
            return hints[word]
    return location


def parse(text: str, source: dict | None = None, today: date | None = None) -> list[Event]:
    source = source or {}
    hints = dict(source.get("venue_hints", {}))
    foreign = re.compile("|".join(source.get("foreign_words", DEFAULT_FOREIGN)), re.I)
    since = (today - timedelta(days=60)) if today else None  # kalender ulatub aastate taha; vanu ei loe
    events: list[Event] = []
    for block in _unfold(text).split("BEGIN:VEVENT")[1:]:
        title = _field(block, "SUMMARY")
        dtstart = _field(block, "DTSTART")
        if not title or not dtstart:
            continue
        cats = [c.strip() for c in _field(block, "CATEGORIES").split(",") if c.strip()]
        location = _field(block, "LOCATION")
        if SKIP.search(title) or (cats and set(cats) <= SKIP_CATEGORIES) or foreign.search(f"{title} {location}"):
            continue
        start, all_day = _when(dtstart)
        if since and start.date() < since:
            continue
        end = None
        if _field(block, "DTEND"):
            last, end_all_day = _when(_field(block, "DTEND"))
            end = (last - timedelta(days=1)).date() if end_all_day else last.date()
        league = next((c for c in cats if c not in SKIP_CATEGORIES), "Motosport")
        level = 4 if YOUTH.search(title) else 3 if CLUB.search(title) else 1
        events.append(new_event(
            source=NAME, sport=SPORT, league=league, start=start, home=title.replace("“", "„"), away="",
            venue=_venue(title, location, hints), city="", url=_field(block, "URL") or "https://msport.ee/kalender/",
            time_tbc=all_day, level=level, end=end,
        ))
    return events


def fetch(fetcher, source: dict | None = None) -> list[Event]:
    return parse(fetcher.get(URL), source, datetime.now(TALLINN).date())
