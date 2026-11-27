"""Lugude detektor: üllatused, seeriad, tasavägised mängud, rekordid. Sisendiks tulemusega mängud, väljundiks sõnastikud (JSON-sõbralikud).

Kõik arvutused tehakse ala, liiga ja hooaja kaupa (hooaeg: jalgpallis kalendriaasta, teistel alal juulist juulini). Tabelit andmetes pole:
see arvutatakse tulemustest (`tulemus.liigapunktid`), seega on üllatused ja seeriad ainult nii täpsed, kui liiga mängud on andmetes täielikud
(`usaldusvaarne` märgib liigad, kus on vähemalt 6 meeskonda, kellel on vähemalt 4 mängu).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from math import ceil

from . import tulemus as tul

MIN_MANGE = 4        # tabeli järjestuses osalemiseks vajalik mängude arv
MIN_MEESKONDI = 6    # väiksemas liigas tabeliüllatust ei tuvasta
SEERIA_MIN = 5       # võidu- ja kaotusseeria alumine piir
KAOTUSETA_MIN = 8    # kaotuseta / võiduta seeria alumine piir (viigiga aladel)
TASE = {1: "Tipp", 2: "Esiliigad", 3: "Madalamad liigad", 4: "Noored", 5: "Koondised"}
PEAMISED = (1, 2, 5)  # raportis ees; noored ja madalamad liigad eraldi osas


def hooaeg(sport: str, d: date) -> str:
    if sport == "jalgpall":
        return str(d.year)
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}/{y + 1}"


@dataclass
class Mang:
    id: str
    sport: str
    liiga: str
    hooaeg: str
    paev: date
    jarjekord: tuple
    kodu: str
    kylaline: str
    t: tul.Tulemus
    tase: int
    url: str = ""
    koht: str = ""

    @property
    def tekst(self) -> str:
        return f"{self.kodu} – {self.kylaline} {self.t.tekst}"


def mangud(events, teams) -> list[Mang]:
    """Tulemusega meeskonnamängud (Event-objektid), meeskonnanimed ühtlustatud."""
    out = []
    for e in events:
        t = tul.parse(e.sport, e.result) if e.away else None
        if not t:
            continue
        d = e.start.date()
        out.append(Mang(e.id, e.sport, e.league, hooaeg(e.sport, d), d, (e.start.isoformat(), e.id),
                        teams.canonical(e.sport, e.home), teams.canonical(e.sport, e.away), t, e.level, e.url, e.venue))
    return sorted(out, key=lambda m: m.jarjekord)


def _grupid(ms: list[Mang]):
    g: dict[tuple, list[Mang]] = defaultdict(list)
    for m in ms:
        g[(m.sport, m.liiga, m.hooaeg)].append(m)
    return g


def usaldusvaarne(ms: list[Mang]) -> bool:
    """Liiga tabeli arvutamine on mõttekas: vähemalt MIN_MEESKONDI meeskonda, kellel on vähemalt MIN_MANGE mängu."""
    n: dict[str, int] = defaultdict(int)
    for m in ms:
        n[m.kodu] += 1
        n[m.kylaline] += 1
    return sum(1 for v in n.values() if v >= MIN_MANGE) >= MIN_MEESKONDI


def ullatused(ms: list[Mang], algus: date, lopp: date) -> list[dict]:
    """Madalamal (punktid mängu kohta) olev meeskond võidab kõrgemat. Koht = järjestus enne mängu, kus on ainult MIN_MANGE+ mänguga meeskonnad;
    üllatus, kui võitja koht on kaotajast vähemalt `max(3, ⌈meeskondi/3⌉)` kohta halvem."""
    out = []
    for (sport, liiga, hoo), games in _grupid(ms).items():
        if not usaldusvaarne(games):
            continue
        pts: dict[str, int] = defaultdict(int)
        played: dict[str, int] = defaultdict(int)
        for m in games:
            if algus <= m.paev <= lopp and tul.voitja(m.t) != "viik":
                ranked = sorted((t for t in played if played[t] >= MIN_MANGE),
                                key=lambda t: (-pts[t] / played[t], -pts[t], t))
                if m.kodu in ranked and m.kylaline in ranked and len(ranked) >= MIN_MEESKONDI:
                    rank = {t: i + 1 for i, t in enumerate(ranked)}
                    win, lose = (m.kodu, m.kylaline) if tul.voitja(m.t) == "kodu" else (m.kylaline, m.kodu)
                    gap = max(3, ceil(len(ranked) / 3))
                    if rank[win] - rank[lose] >= gap:
                        out.append({"mang": m.tekst, "id": m.id, "sport": sport, "liiga": liiga, "tase": m.tase, "paev": m.paev.isoformat(),
                                    "voitja": win, "voitja_koht": rank[win], "kaotaja": lose, "kaotaja_koht": rank[lose],
                                    "meeskondi": len(ranked), "tulemus": m.t.tekst, "koht_vahe": rank[win] - rank[lose]})
            kp, gp = tul.liigapunktid(sport, m.t)
            pts[m.kodu] += kp
            pts[m.kylaline] += gp
            played[m.kodu] += 1
            played[m.kylaline] += 1
    return sorted(out, key=lambda x: (x["tase"], -x["koht_vahe"]))


def _tulemused_meeskonniti(games: list[Mang]) -> dict[str, list[tuple[Mang, str]]]:
    """meeskond → [(mäng, V/K/X)] kronoloogiliselt."""
    seq: dict[str, list[tuple[Mang, str]]] = defaultdict(list)
    for m in games:
        w = tul.voitja(m.t)
        a, b = ("V", "K") if w == "kodu" else (("K", "V") if w == "külaline" else ("X", "X"))
        seq[m.kodu].append((m, a))
        seq[m.kylaline].append((m, b))
    return seq


def _pikim(seq: list[tuple[Mang, str]], tahed: str, lopp: date | None = None):
    """(pikkus, algus-mäng, lõpu-mäng, jätkub) pikim järjest tähtedega `tahed` jada; `lopp` piirab mängud kuupäevani."""
    best = (0, None, None, False)
    run = []
    items = [(m, r) for m, r in seq if lopp is None or m.paev <= lopp]
    for i, (m, r) in enumerate(items):
        if r in tahed:
            run.append(m)
            if len(run) > best[0]:
                best = (len(run), run[0], run[-1], i == len(items) - 1)
        else:
            run = []
    return best


def _aktiivne(seq: list[tuple[Mang, str]], tahed: str, lopp: date) -> list[Mang]:
    items = [(m, r) for m, r in seq if m.paev <= lopp]
    run: list[Mang] = []
    for m, r in reversed(items):
        if r in tahed:
            run.append(m)
        else:
            break
    return list(reversed(run))


def seeriad(ms: list[Mang], algus: date, lopp: date) -> dict[str, list[dict]]:
    """Akiivsed seeriad akna lõpu seisuga (`jatkub`) ja aknas katkenud seeriad (`katkes`)."""
    jatkub, katkes = [], []
    for (sport, liiga, hoo), games in _grupid(ms).items():
        sure = usaldusvaarne(games)
        for team, seq in _tulemused_meeskonniti(games).items():
            drawsport = sport in tul.DRAWS
            tyyp = [("võidud", "V", SEERIA_MIN), ("kaotused", "K", SEERIA_MIN)]
            if drawsport:
                tyyp += [("kaotuseta", "VX", KAOTUSETA_MIN), ("võiduta", "KX", KAOTUSETA_MIN)]
            vseq = {n: _aktiivne(seq, tahed, lopp) for n, tahed, _ in tyyp}
            for nimi, tahed, minimum in tyyp:
                run = vseq[nimi]
                if nimi == "kaotuseta" and len(run) <= len(vseq["võidud"]):
                    continue
                if nimi == "võiduta" and len(run) <= len(vseq["kaotused"]):
                    continue
                if len(run) >= minimum:
                    sel_nadalal = any(algus <= m.paev <= lopp for m in run)
                    if not sel_nadalal:
                        continue   # liiga hooaeg on lõppenud või meeskond ei mänginud: see pole nädala lugu
                    jatkub.append({"meeskond": team, "sport": sport, "liiga": liiga, "tase": run[-1].tase, "tyyp": nimi, "pikkus": len(run),
                                   "sel_nadalal_pikenes": sel_nadalal, "viimane": run[-1].tekst, "paev": run[-1].paev.isoformat(),
                                   "usaldusvaarne": sure})
            # aknas katkenud: seeria enne akna esimest mängu (võidud/kaotused), mille akna mäng katkestas
            before = [(m, r) for m, r in seq if m.paev < algus]
            inside = [(m, r) for m, r in seq if algus <= m.paev <= lopp]
            if not inside or not before:
                continue
            for nimi, tahed, minimum in tyyp[:2]:
                run = _aktiivne(before, tahed, algus)
                if len(run) >= minimum and inside[0][1] not in tahed:
                    katkes.append({"meeskond": team, "sport": sport, "liiga": liiga, "tase": run[-1].tase, "tyyp": nimi, "pikkus": len(run),
                                   "katkestas": inside[0][0].tekst, "paev": inside[0][0].paev.isoformat(), "usaldusvaarne": sure})
    key = lambda x: (x["tase"], -x["pikkus"], x["meeskond"])
    return {"jatkub": sorted(jatkub, key=key), "katkes": sorted(katkes, key=key)}


def tasavagised(ms: list[Mang], algus: date, lopp: date) -> list[dict]:
    out = []
    for m in ms:
        if algus <= m.paev <= lopp:
            why = tul.tasavagine(m.sport, m.t)
            if why:
                out.append({"mang": m.tekst, "id": m.id, "sport": m.sport, "liiga": m.liiga, "tase": m.tase, "paev": m.paev.isoformat(),
                            "tulemus": m.t.tekst, "pohjus": why, "vahe": m.t.vahe, "kokku": m.t.kokku})
    return sorted(out, key=lambda x: (x["tase"], x["vahe"], -x["kokku"]))


def rekordid(ms: list[Mang], algus: date, lopp: date, min_tulemusi: int = 10) -> list[dict]:
    """Ala ja hooaja kaupa: suurim skoor mängus, suurim vahe, pikim võiduseeria; kahes ulatuses: „kõik“ liigad ja „tipp“ (tase 1, 2, 5:
    tipp- ja esiliigad, koondised). `uus` = püstitati (v.a võrdsustamine) aknas."""
    out = []
    for ulatus, lubatud in (("kõik", None), ("tipp", PEAMISED)):
        by_sport: dict[tuple, list[Mang]] = defaultdict(list)
        for m in ms:
            if lubatud is None or m.tase in lubatud:
                by_sport[(m.sport, m.hooaeg)].append(m)
        for (sport, hoo), games in by_sport.items():
            if len(games) < min_tulemusi:
                continue
            unit = tul.UNITS_PL[tul.UNITS[sport]]
            # võrkpallis on skoor setid (kuni 5, vahe kuni 3): „rekord“ oleks triviaalne, seega ainult seeria
            kategooriad = () if sport == "vorkpall" else (("suurim skoor", lambda m: m.t.kokku, f"{unit} kokku"),
                                                           ("suurim vahe", lambda m: m.t.vahe, f"{unit} vahe"))
            for kategooria, key, label in kategooriad:
                best = max(key(m) for m in games)
                prev = [key(m) for m in games if m.paev < algus]
                holders = [m for m in games if key(m) == best]
                in_window = [m for m in holders if algus <= m.paev <= lopp]
                m = in_window[0] if in_window else holders[0]
                out.append({"ulatus": ulatus, "sport": sport, "hooaeg": hoo, "kategooria": kategooria, "vaartus": best, "ühik": label,
                            "mang": m.tekst, "liiga": m.liiga, "tase": m.tase, "paev": m.paev.isoformat(),
                            "uus": bool(in_window) and (not prev or best > max(prev)),
                            "voordsustas": bool(in_window) and bool(prev) and best == max(prev), "mitu_hoidjat": len(holders)})
            # pikim võiduseeria (liiga piires), ainult usaldusväärsetes liigades
            parim = None
            eelmine = 0
            eile = algus.fromordinal(algus.toordinal() - 1)
            for (s2, liiga, h2), lg in _grupid(games).items():
                if not usaldusvaarne(lg):
                    continue
                for team, seq in _tulemused_meeskonniti(lg).items():
                    n, first, last, ongoing = _pikim(seq, "V")
                    eelmine = max(eelmine, _pikim(seq, "V", eile)[0])
                    if parim is None or n > parim[0]:
                        parim = (n, last, ongoing, team)
            if parim and parim[0] >= SEERIA_MIN:
                n, last, ongoing, team = parim
                out.append({"ulatus": ulatus, "sport": sport, "hooaeg": hoo, "kategooria": "pikim võiduseeria", "vaartus": n,
                            "ühik": "võitu järjest", "mang": team, "liiga": last.liiga, "tase": last.tase, "paev": last.paev.isoformat(),
                            "uus": algus <= last.paev <= lopp and n > eelmine, "voordsustas": False, "mitu_hoidjat": 1, "jatkub": ongoing})
    return sorted(out, key=lambda x: (x["ulatus"] != "tipp", x["sport"], x["kategooria"]))
