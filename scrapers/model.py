"""Ühtne andmemudel, mille iga adapter tagastab."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import sports

TALLINN = ZoneInfo("Europe/Tallinn")

# tase → nimi valikus, kaust, pealkirja algus ja sõnavormid lausetesse:
#   to:    päise lauses "Ela kaasa koondistele …" (alaleütlev)
#   games: "tippvõistlused" (sissejuhatus, kirjeldus, "Selle päeva … →")
#   one:   "Täna ei ole Tallinnas ühtegi tippvõistlust."
#   many:  "Järgmise kahe nädala jooksul ei ole Tallinnas saalihoki tippvõistlusi."
# Tase 1 on pallimängudes kõrgliigad, ürituste aladel täiskasvanute tippvõistlused (MV, KV, rahvusvahelised).
# Kaust jääb "korgliigad/", et vanad lingid töötaksid.
DEFAULT_LEVEL = 0  # avaleht: kõik liigad (lehe juurkaust); muudetav config.toml [site] default_level
LEVELS = {
    # 0 = kõik valikus näidatavad tasemed ühes nimekirjas (peidetud taset ei loeta)
    0: {"name": "Kõik liigad", "slug": "koik", "title": "Kõik spordimängud", "to": "spordiüritustele",
        "games": "kõik mängud", "one": "mängu", "many": "mänge", "all": True},
    1: {"name": "Tippvõistlused", "slug": "korgliigad", "title": "Tippsport", "to": "tippvõistlustele",
        "games": "tippvõistlused", "one": "tippvõistlust", "many": "tippvõistlusi"},
    2: {"name": "Esiliigad", "slug": "esiliigad", "title": "Esiliigade mängud", "to": "esiliigadele",
        "games": "esiliigade mängud", "one": "esiliigamängu", "many": "esiliigamänge"},
    3: {"name": "Madalamad liigad", "slug": "madalamad", "title": "Madalamate liigade mängud", "to": "madalamatele liigadele",
        "games": "madalamate liigade mängud", "one": "madalama liiga mängu", "many": "madalamate liigade mänge",
        "hidden": True},  # ajutiselt peidus valikust; lehed ehitatakse edasi
    4: {"name": "Noored", "slug": "noored", "title": "Noorte mängud", "to": "noortele",
        "games": "noorte mängud", "one": "noortemängu", "many": "noortemänge"},
    5: {"name": "Koondised", "slug": "koondised", "title": "Koondiste mängud", "to": "koondistele",
        "games": "koondiste mängud", "one": "koondisemängu", "many": "koondisemänge"},
}


def levels_for(default_level: int = DEFAULT_LEVEL) -> dict[int, dict]:
    """LEVELS koos kaustaga: vaiketase on lehe juurkaustas, teised oma kaustas (nt "esiliigad/")."""
    return {k: dict(v, prefix="" if k == default_level else f"{v['slug']}/") for k, v in LEVELS.items()}


for _k, _v in levels_for().items():  # tagasiühilduvus: LEVELS[k]["prefix"] vaikeseadega
    LEVELS[_k]["prefix"] = _v["prefix"]

# alade register: sports.toml (üks ala = üks plokk; vt scrapers/sports.py)
SPORTS = sports.SPORTS

# alad, kus real on üritus (võistlus, etapp), mitte kahe võistkonna mäng: home = ürituse nimi, away tühi
# (lauatennises on ka meistriliiga mängud, seepärast seda seal pole: `event = true` ainult ürituse aladel)
EVENT_SPORTS = sports.EVENT_SPORTS


@dataclass(frozen=True)
class Event:
    id: str  # stabiilne räsi (allikas + kuupäev + võistkonnad)
    sport: str  # võti SPORTS sõnastikust
    league: str  # inimloetav liiga nimi
    start: datetime  # ajavööndiga, Europe/Tallinn
    home: str
    away: str
    venue: str  # normaliseeritud saali nimi
    city: str  # "Tallinn"
    url: str  # link allika mängulehele (või liiga kalendrile)
    source: str  # adapteri nimi
    time_tbc: bool = False  # True, kui kellaaeg pole veel kinnitatud
    result: str = ""  # lõppseis "kodu-võõras" (nt "3-0"; jäähokis võib lõpus olla "OT" või "SO"), tühi kuni mäng on mängitud või kui allikas seda ei anna
    level: int = 1  # 1 = kõrgliiga, 2 = esiliiga, 3 = madalamad liigad, 4 = noored, 5 = koondised (igaühel eraldi kalender)
    end: str = ""  # mitmepäevase ürituse viimane päev "YYYY-MM-DD"; tühi = ühepäevane
    # ülekanne: link otseülekandele (tulevane mäng) või järelvaatamisele (peetud mäng) ja kes näitab
    # ("YouTube", "Postimees", "Delfi TV"). Tühi, kui ei tea. Vt ulekanded.py.
    video: str = ""
    video_by: str = ""
    # märkus mängu real ja lehel (nt „Info telekavast: kontrolli algusaega ja toimumiskohta“); tühi = pole
    note: str = ""

    def __post_init__(self) -> None:
        if self.sport not in SPORTS:
            raise ValueError(f"Tundmatu ala: {self.sport!r}")
        if self.start.tzinfo is None:
            raise ValueError("start peab olema ajavööndiga")
        if self.end and date.fromisoformat(self.end) <= self.start.date():
            raise ValueError("end peab olema hilisem kui alguspäev (ühepäevasel jäta tühjaks)")

    @property
    def last_day(self) -> date:
        """Viimane päev: ühepäevasel alguspäev, mitmepäevasel `end`."""
        return date.fromisoformat(self.end) if self.end else self.start.date()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.astimezone(TALLINN).isoformat()
        for key in ("end", "video", "video_by", "note"):
            if not d[key]:
                del d[key]  # tühjana välja ei kirjutata: olemasolevad andmefailid ei muutu
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        d = dict(d)
        d["start"] = datetime.fromisoformat(d["start"]).astimezone(TALLINN)
        return cls(**d)


def make_id(source: str, start: datetime, home: str, away: str) -> str:
    """Stabiilne ID: sama mäng saab igal kogumisel sama ID, kui kuupäev ja võistkonnad ei muutu."""
    key = "|".join([source, start.astimezone(TALLINN).date().isoformat(), home.strip().lower(), away.strip().lower()])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def new_event(
    *,
    source: str,
    sport: str,
    league: str,
    start: datetime,
    home: str,
    away: str,
    venue: str,
    city: str,
    url: str,
    time_tbc: bool = False,
    level: int = 1,
    result: str = "",
    end: date | None = None,
    video: str = "",
    video_by: str = "",
    note: str = "",
) -> Event:
    """Mugav konstruktor adapteritele: arvutab ID ja viib aja Tallinna ajavööndisse."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=TALLINN)
    start = start.astimezone(TALLINN)
    home, away = home.strip(), away.strip()
    return Event(
        id=make_id(source, start, home, away),
        sport=sport,
        league=league,
        start=start,
        home=home,
        away=away,
        venue=venue,
        city=city,
        url=url,
        source=source,
        time_tbc=time_tbc,
        level=level,
        result=result,
        end=end.isoformat() if end and end > start.date() else "",
        video=video.strip() if video else "",
        video_by=video_by.strip() if video and video_by else "",
        note=note.strip(),
    )


_SCORE = re.compile(r"(\d{1,3})\s*[-–:]\s*(\d{1,3})")


def parse_score(text: str) -> str:
    """"3 - 0" → "3-0". Tühi tekst või "-" (mäng pole veel mängitud) → "". """
    m = _SCORE.search(text or "")
    return f"{int(m.group(1))}-{int(m.group(2))}" if m else ""
