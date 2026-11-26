"""Ülekannete kava: Go3 spordikanalid (Go3 Sport 1–4, Go3 Sport Open). Go3 on tasuline.

go3.ee „Otse TV“ leht laeb kava avalikust JSON-API-st (sisselogimist pole vaja, robots.txt keelab ainult
/monitoring/ ja */ghost/*):
  https://go3.ee/api/products/lives/programmes?liveId[]=<kanal>&…&since=<päeva algus>&till=<päeva lõpp>&…
Vastus on saadete nimekiri: {"title": "FIBA Basketball World Cup Qualifiers. Eesti - Prantsusmaa",
"since": "2026-11-27T16:50:00Z", "liveProgramme": true, "genres": [{"name": "Korvpall"}], "live": {"id": …}}.
Pikemat vahemikku kui üks päev API ei luba. Küsime ainult spordikanaleid (vastus on väike) ja DAYS päeva.

Ainult otseülekanded (liveProgramme = true): kordused jäävad välja. ETV/ETV2 kava tuleb ERR-ist (kava_err),
seda Go3-st ei loeta. Sama mängu tasuta ülekanne (ERR) jääb lehel esimeseks (ulekanded.match: kanalite järjekord).
See EI OLE mängude allikas: kava read seotakse ainult olemasolevate mängudega.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timedelta
from urllib.parse import quote

from . import sports
from .http import FetchError
from .model import TALLINN

log = logging.getLogger(__name__)

NAME = "kava_go3"
BY = "Go3 (tasuline)"
DAYS = 8  # täna + 7 päeva
PAGE = "https://go3.ee/live_tv"
CHANNELS = {4296024: "Go3 Sport 1", 4231570: "Go3 Sport 2", 4150367: "Go3 Sport 3", 7016367: "Go3 Sport 4",
            2275257: "Go3 Sport Open"}
URL = "https://go3.ee/api/products/lives/programmes?{ids}&since={since}&till={till}&platform=BROWSER&lang=ET&tenant=OM_EE"

GENRES = sports.GO3_GENRES   # žanr → ala (registri `go3` väljad, sports.toml)


def sport_of(genres: list) -> str:
    for g in genres or []:
        name = (g.get("name") or "").strip().lower() if isinstance(g, dict) else ""
        if name in GENRES:
            return GENRES[name]
    return ""


def _teams(title: str) -> tuple[str, str] | None:
    rest = title.rsplit(". ", 1)[-1] if ". " in title else title.split(": ", 1)[-1]
    for sep in (" - ", " – ", " — "):
        if sep in rest:
            home, away = rest.split(sep, 1)
            if home.strip() and away.strip():
                return home.strip(), away.strip()
    return None


def parse(text: str) -> list[dict]:
    """Ühe päeva kava pallimängude otseülekanded: {"start", "sport", "home", "away", "url", "by"}."""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"Go3 kava: ootamatu vastus {str(data)[:120]}")
    out = []
    for p in data:
        if not p.get("liveProgramme") or not p.get("since"):
            continue
        sport = sport_of(p.get("genres"))
        teams = _teams((p.get("title") or "").strip()) if sport else None
        if not teams:
            continue
        start = datetime.fromisoformat(p["since"].replace("Z", "+00:00")).astimezone(TALLINN)
        out.append({"start": start, "sport": sport, "home": teams[0], "away": teams[1], "url": PAGE, "by": BY})
    return out


def day_url(d: date) -> str:
    """Päeva kava päring Tallinna aja järgi ("2026-11-27T00:00+0200" … "T23:59+0200", suvel +0300)."""
    ids = "&".join(f"liveId[]={i}" for i in CHANNELS)
    since, till = (datetime.combine(d, t, TALLINN).strftime("%Y-%m-%dT%H:%M%z") for t in (time(0), time(23, 59)))
    return URL.format(ids=ids, since=quote(since), till=quote(till))


def fetch(fetcher, today: date | None = None) -> list[dict]:
    today = today or datetime.now(TALLINN).date()
    rows: list[dict] = []
    ok = 0
    for i in range(DAYS):
        d = today + timedelta(days=i)
        try:
            rows.extend(parse(fetcher.get(day_url(d))))
            ok += 1
        except (FetchError, ValueError) as exc:
            log.warning("%s: %s kava ei saanud: %s", NAME, d, exc)
    if not ok:
        raise FetchError("Go3 kava: ükski päring ei õnnestunud")
    return rows
