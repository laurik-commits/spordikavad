"""Elo reiting ja tagasivaatav test (jalgpall: võit / viik / kaotus).

Põhimõte: iga mängu ennustatakse ainult andmetega, mis olid teada enne seda mängu (mängud järjestatud alguse järgi, reiting uuendatakse
alles pärast ennustust). Reiting on liigapõhine, kõik algavad 1500-lt.

Mudel: x = (reiting_kodu − reiting_külaline + kodueelis) · ln10/400; P(kodu) = σ(x − c), P(külaline) = σ(−x − c), P(viik) = ülejäänu
(järjestatud logit; c määrab viigi tõenäosuse). Uuendus: K · (tegelik − oodatud), tegelik 1 / ½ / 0, oodatud = P(kodu) + ½·P(viik).
Hooaja vahetusel `taandumine` osa reitingust tõmmatakse keskmise poole (andmetes on praegu ainult üks hooaeg, seega seda ei testita).

Parameetreid (K, kodueelis, c) ei häälestata testitava liiga andmete peal: need valitakse teiste liigade põhjal (`haalesta`).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from . import tulemus as tul

ALGUS = 1500.0
LN10_400 = math.log(10) / 400
OUTCOMES = ("kodu", "viik", "kylaline")


@dataclass(frozen=True)
class Parameetrid:
    k: float = 20.0
    kodueelis: float = 60.0
    c: float = 0.5
    taandumine: float = 0.33


def sigma(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def tõenäosused(r_kodu: float, r_kyl: float, p: Parameetrid) -> tuple[float, float, float]:
    x = (r_kodu - r_kyl + p.kodueelis) * LN10_400
    ph, pa = sigma(x - p.c), sigma(-x - p.c)
    return ph, max(0.0, 1.0 - ph - pa), pa


def tõenäosused_kaks(r_kodu: float, r_kyl: float, p: Parameetrid) -> tuple[float, float, float]:
    """Alad ilma viigita (võrkpall): P(kodu) = σ(x), P(viik) = 0, P(külaline) = 1 − P(kodu); x = (reitingute vahe + kodueelis) · ln10/400."""
    ph = sigma((r_kodu - r_kyl + p.kodueelis) * LN10_400)
    return ph, 0.0, 1.0 - ph


def tegelik(m) -> str:
    """„kodu“ | „viik“ | „kylaline“ (ilma täpitähtedeta, et sobiks mudeli väljundi võtmetega)."""
    w = tul.voitja(m.t)
    return "kylaline" if w == "külaline" else w


def taanda(rat: dict[str, float], osa: float) -> None:
    """Hooaja vahetus: reiting tõmmatakse liiga keskmise poole."""
    if not rat:
        return
    kesk = sum(rat.values()) / len(rat)
    for t in rat:
        rat[t] = rat[t] + (kesk - rat[t]) * osa


def kaiguta(games, p: Parameetrid):
    """Järjest läbi `games` (ühe liiga mängud, ajajärjekorras). Annab iga mängu kohta (mäng, (P_kodu, P_viik, P_külaline), tegelik,
    mänge_kodul_enne, mänge_külalisel_enne). Ennustus tehakse enne uuendust."""
    rat: dict[str, float] = defaultdict(lambda: ALGUS)
    mange: dict[str, int] = defaultdict(int)
    hooaeg = None
    for m in games:
        if hooaeg is not None and m.hooaeg != hooaeg:
            taanda(rat, p.taandumine)
        hooaeg = m.hooaeg
        pr = tõenäosused(rat[m.kodu], rat[m.kylaline], p)
        w = tegelik(m)
        yield m, pr, w, mange[m.kodu], mange[m.kylaline]
        s = {"kodu": 1.0, "viik": 0.5, "kylaline": 0.0}[w]
        d = p.k * (s - (pr[0] + 0.5 * pr[1]))
        rat[m.kodu] += d
        rat[m.kylaline] -= d
        mange[m.kodu] += 1
        mange[m.kylaline] += 1


def liigad(ms, sport: str = "jalgpall") -> dict[tuple[str, str], list]:
    """{(liiga, hooaeg): mängud ajajärjekorras}, ainult need, kus on tabel arvutatav ja mänge piisavalt."""
    g: dict[tuple[str, str], list] = defaultdict(list)
    for m in ms:
        if m.sport == sport:
            g[(m.liiga, m.hooaeg)].append(m)
    return g


# ---- võrdlusalused ----------------------------------------------------------------------------------------------------

def tabeli_ennustus(games):
    """„Tabelis kõrgemal olev võidab“: punktid mängu kohta enne mängu (3/1/0), viigi korral võidab kodu. Annab (mäng, valik, tegelik, mänge_k, mänge_g)."""
    pts: dict[str, int] = defaultdict(int)
    n: dict[str, int] = defaultdict(int)
    for m in games:
        a = pts[m.kodu] / n[m.kodu] if n[m.kodu] else 0.0
        b = pts[m.kylaline] / n[m.kylaline] if n[m.kylaline] else 0.0
        valik = "kylaline" if b > a else "kodu"
        yield m, valik, tegelik(m), n[m.kodu], n[m.kylaline]
        kp, gp = tul.liigapunktid(m.sport, m.t)
        pts[m.kodu] += kp
        pts[m.kylaline] += gp
        n[m.kodu] += 1
        n[m.kylaline] += 1


def sagedused(games) -> tuple[float, float, float]:
    n = len(games) or 1
    c = defaultdict(int)
    for m in games:
        c[tegelik(m)] += 1
    return c["kodu"] / n, c["viik"] / n, c["kylaline"] / n


# ---- mõõdikud ----------------------------------------------------------------------------------------------------------

def brier(pr: tuple[float, float, float], w: str) -> float:
    """Kolme tulemuse Brier: Σ(p − tegelik)², 0 = täiuslik, 2 = kõige halvem; „alati sama jaotus“ ≈ 0,6."""
    return sum((p - (1.0 if o == w else 0.0)) ** 2 for p, o in zip(pr, OUTCOMES))


def logloss(pr, w: str) -> float:
    return -math.log(max(pr[OUTCOMES.index(w)], 1e-9))


def tapsus(pr, w: str) -> bool:
    return OUTCOMES[max(range(3), key=lambda i: pr[i])] == w


def hinda(rows) -> dict:
    """rows: [(pr, w)] → täpsus (kõrgeima tõenäosusega tulemus), Brier, log-kaotus."""
    n = len(rows)
    if not n:
        return {"n": 0}
    return {"n": n, "tapsus": sum(tapsus(p, w) for p, w in rows) / n,
            "brier": sum(brier(p, w) for p, w in rows) / n, "logloss": sum(logloss(p, w) for p, w in rows) / n}


def kalibratsioon(rows, bins: int = 10) -> list[dict]:
    """Kodu võidu tõenäosus: ennustatud keskmine vs tegelik osakaal kastide kaupa."""
    kastid: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for p, w in rows:
        kastid[min(bins - 1, int(p[0] * bins))].append((p[0], 1 if w == "kodu" else 0))
    out = []
    for b in sorted(kastid):
        xs = kastid[b]
        out.append({"alates": b / bins, "kuni": (b + 1) / bins, "n": len(xs),
                    "ennustatud": sum(x for x, _ in xs) / len(xs), "tegelik": sum(y for _, y in xs) / len(xs)})
    return out


# ---- häälestus teistel liigadel ----------------------------------------------------------------------------------------

GRID_K = (10, 20, 30, 40, 60, 80)
GRID_H = (30, 60, 90, 120)
GRID_C = (0.1, 0.2, 0.3, 0.5, 0.7)


def _brier_liigad(grupid: list[list], p: Parameetrid, vahele: int = 0) -> float:
    s = n = 0
    for games in grupid:
        for m, pr, w, a, b in kaiguta(games, p):
            if a >= vahele and b >= vahele:
                s += brier(pr, w)
                n += 1
    return s / n if n else float("inf")


def haalesta(grupid: list[list], vahele: int = 0) -> tuple[Parameetrid, float]:
    """Parameetrid, mis minimeerivad Brier skoori antud (testimisest väljajäetud) liigadel."""
    parim = (Parameetrid(), float("inf"))
    for k, h, c in product(GRID_K, GRID_H, GRID_C):
        p = Parameetrid(k=k, kodueelis=h, c=c)
        v = _brier_liigad(grupid, p, vahele)
        if v < parim[1]:
            parim = (p, v)
    return parim


def bootstrap_vahe(a: list[float], b: list[float], kordi: int = 2000, seed: int = 7) -> tuple[float, float, float]:
    """Paarisbootstrap: (keskmine vahe, 2,5%, 97,5%) mängu kohta Brier(a) − Brier(b)."""
    import random
    rnd = random.Random(seed)
    n = len(a)
    d = [x - y for x, y in zip(a, b)]
    keskmised = sorted(sum(d[rnd.randrange(n)] for _ in range(n)) / n for _ in range(kordi))
    return sum(d) / n, keskmised[int(0.025 * kordi)], keskmised[int(0.975 * kordi)]
