"""Tulemuste ühtlustus: kõigil aladel sama `kodu-võõras` kuju (+ valikuline `OT`/`SO`), siit tuletatud mõisted ala kaupa.

Mõisted (sama sisu eri aladel):
- võitja: „kodu“, „külaline“ või „viik“ (viik ainult aladel, kus see on võimalik: jalgpall, saalijalgpall, käsipall, saalihoki);
- vahe: skooride vahe absoluutväärtus (väravad, punktid või setid; võrkpallis setivahe, mitte punktivahe);
- kokku: skooride summa (väravaid/punkte/sete kokku);
- liigapunktid: tabeli arvutamiseks (ala reeglid on hinnanguline, sest allikad punkte ei anna).
Seteriti punkte (võrkpall), lisaaja (peale jäähoki) ega penaltiseeriat andmetes pole.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

RESULT_SPORTS = {"jalgpall", "saalijalgpall", "kasipall", "korvpall", "vorkpall", "jaahoki", "saalihoki"}
DRAWS = {"jalgpall", "saalijalgpall", "kasipall", "saalihoki"}
UNITS = {"jalgpall": "värav", "saalijalgpall": "värav", "saalihoki": "värav", "jaahoki": "värav", "kasipall": "värav",
         "korvpall": "punkt", "vorkpall": "set"}
UNITS_PL = {"värav": "väravat", "punkt": "punkti", "set": "setti"}
_RESULT = re.compile(r"^(\d+)-(\d+)(?:\s*(OT|SO))?$")


@dataclass(frozen=True)
class Tulemus:
    kodu: int
    kylaline: int
    lisa: str = ""   # "", "OT" (lisaaeg), "SO" (karistuslaskmised); ainult jäähokis

    @property
    def vahe(self) -> int:
        return abs(self.kodu - self.kylaline)

    @property
    def kokku(self) -> int:
        return self.kodu + self.kylaline

    @property
    def tekst(self) -> str:
        return f"{self.kodu}:{self.kylaline}" + (f" {self.lisa}" if self.lisa else "")


def parse(sport: str, text: str) -> Tulemus | None:
    """`Event.result` → Tulemus. None, kui tulemust pole, see on vigane või ala ei toeta tulemusi (võrdne skoor alal ilma viigita on andmeviga)."""
    if sport not in RESULT_SPORTS:
        return None
    m = _RESULT.match((text or "").strip())
    if not m:
        return None
    t = Tulemus(int(m.group(1)), int(m.group(2)), m.group(3) or "")
    if t.kodu == t.kylaline and sport not in DRAWS:
        return None
    return t


def voitja(t: Tulemus) -> str:
    return "viik" if t.kodu == t.kylaline else ("kodu" if t.kodu > t.kylaline else "külaline")


def liigapunktid(sport: str, t: Tulemus) -> tuple[int, int]:
    """(kodu, külaline) tabelipunktid. Hinnanguline: jalgpall ja saalijalgpall 3/1/0, käsipall 2/1/0, saalihoki 3/1/0,
    korvpall 2/0, jäähoki 3/0 (lisaajaga 2/1), võrkpall 3/0 (3–2: 2/1)."""
    w = voitja(t)
    if w == "viik":
        return (1, 1)
    hi, lo = (t.kodu, t.kylaline) if w == "kodu" else (t.kylaline, t.kodu)
    if sport in ("jalgpall", "saalijalgpall", "saalihoki"):
        win, lose = 3, 0
    elif sport == "kasipall":
        win, lose = 2, 0
    elif sport == "korvpall":
        win, lose = 2, 0
    elif sport == "jaahoki":
        win, lose = (2, 1) if t.lisa else (3, 0)
    elif sport == "vorkpall":
        win, lose = (2, 1) if lo == 2 else (3, 0)
    else:
        win, lose = 3, 0
    return (win, lose) if w == "kodu" else (lose, win)


def tasavagine(sport: str, t: Tulemus) -> str:
    """Põhjus, miks mäng oli tasavägine (tühi = ei olnud). Künnised ala kaupa:
    jalgpall: viik vähemalt 4 väravaga või 1 värava vahe vähemalt 5 väravaga; saalijalgpall ja saalihoki: vahe ≤ 1 ja ≥ 6 väravat;
    käsipall: vahe ≤ 1; korvpall: vahe ≤ 3; võrkpall: 5-setiline (3:2); jäähoki: lisaaeg või karistuslaskmised."""
    if sport == "jalgpall":
        if t.vahe == 0 and t.kokku >= 4:
            return f"viik {t.kodu}:{t.kylaline}"
        if t.vahe == 1 and t.kokku >= 5:
            return "ühe värava vahe, väravarohke"
    elif sport in ("saalijalgpall", "saalihoki") and t.vahe <= 1 and t.kokku >= 6:
        return "viik" if t.vahe == 0 else "ühe värava vahe"
    elif sport == "kasipall" and t.vahe <= 1:
        return "viik" if t.vahe == 0 else "ühe värava vahe"
    elif sport == "korvpall" and t.vahe <= 3:
        return f"{t.vahe} punkti vahe"
    elif sport == "vorkpall" and max(t.kodu, t.kylaline) == 3 and min(t.kodu, t.kylaline) == 2:
        return "viiene set"
    elif sport == "jaahoki" and t.lisa:
        return "lisaaeg" if t.lisa == "OT" else "karistuslaskmised"
    return ""
