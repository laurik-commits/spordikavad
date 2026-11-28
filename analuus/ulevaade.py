"""Mängu lehe automaatne ülevaade (enne ja pärast mängu).

Kõik read on arvutatud andmestikus olevatest tulemustest, kohtadest ja ülekannetest: vigastusi, koosseise, taustalugusid ega piletiandmeid
siin ei ole ega väljamõelda. Ülevaade ei ole tehisintellekti (keelemudeli) kirjutatud, vaid reeglipõhine tekst, mis tuleb samadest andmetest
igal ehitusel ühtmoodi.

Faktid (vorm, omavahelised mängud, arvutatud tabelikoht, koht, järgmised mängud) on kõigil aladel, kus on meeskonnamängud tulemustega
(`tulemus.RESULT_SPORTS`). **Ennustus** (Elo-tüüpi tugevusnumber, vt `ennustus.py`) on ainult alal ja tasemel, mille kohta omanik on selle lubanud
(`ENNUSTA`, `ENNUSTUSE_TASEMED`): jalgpall ja võrkpall, tase 1 (tipp) ja 2 (esiliigad). Noorte-, madalama liiga- ja koondisemängudel tõenäosusi ei näidata
(ei enne ega pärast mängu). Ennustus on meelelahutuslik analüüs, mitte kihlveo nõuanne.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from . import ennustus as en
from . import tulemus as tul
from .lood import MIN_MANGE, hooaeg
from .meeskonnad import Teams

# Jalgpalli Elo parameetrid: häälestusliigad (kõik teised liigad kui testitav) valisid K = 80; tundlikkuse kontroll näitas Brier skoori lamedat
# platood K = 60…120 juures, seega võetud on platoo vasak äär (K = 60). Kodueelis 60, viigi c 0,3.
PARAMS = en.Parameetrid(k=60.0, kodueelis=60.0, c=0.3, taandumine=0.33)
# Võrkpall: viike pole, andmeid on vähe (testi pole võimalik teha); parameetrid on mõõdukad vaikeväärtused ja TESTIMATA (lehel öeldud).
PARAMS_VORK = en.Parameetrid(k=40.0, kodueelis=60.0, c=0.0, taandumine=0.33)
ENNUSTA = {"jalgpall": PARAMS, "vorkpall": PARAMS_VORK}
ENNUSTUSE_TASEMED = (1, 2)
MIN_TABEL_MEESKONDI = 6       # tabeli koha näitamiseks (vähemalt nii mitu meeskonda on jõudnud MIN_MANGE mänguni)
MIN_ENNUSTUS = 3              # ennustus alles siis, kui mõlemal meeskonnal on nii mitu mängu selle liiga andmetes enne mängu
VORM = 5                      # vormi pikkus
OMAVAHELISI = 5               # nii palju omavahelisi mänge näidatakse
HALLI_MIN = 10                # halli statistika alumine piir (tulemusega mänge saalis)

KUU = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober", "november", "detsember"]


def _kp(d: date) -> str:
    return f"{d.day}. {KUU[d.month - 1]}"


def _ph(x: float) -> str:
    return f"{round(x * 100)}%"


@dataclass
class Rec:
    id: str
    sport: str
    liiga: str
    level: int
    hooaeg: str
    start: datetime
    kodu: str
    kyl: str
    venue: str
    t: tul.Tulemus | None
    pr: tuple[float, float, float] = (0.0, 0.0, 0.0)
    r_enne: tuple[float, float] = (en.ALGUS, en.ALGUS)
    r_parast: tuple[float, float] | None = None
    mange_enne: tuple[int, int] = (0, 0)
    tabel: dict = field(default_factory=dict)   # {"kodu": (koht, ppg, mänge), "kyl": ..., "meeskondi": n}

    @property
    def ennusta(self) -> bool:
        """Selle mängu kohta tohib tõenäosusi näidata (ala ja tase on lubatud)."""
        return self.sport in ENNUSTA and self.level in ENNUSTUSE_TASEMED

    @property
    def viigiga(self) -> bool:
        return self.sport in tul.DRAWS


def _voit(t: tul.Tulemus, kodu_poolt: bool) -> str:
    """V = võit, X = viik, K = kaotus meeskonna vaates."""
    w = tul.voitja(t)
    if w == "viik":
        return "X"
    return "V" if (w == "kodu") == kodu_poolt else "K"


def _toenaosused(r_kodu: float, r_kyl: float, p: en.Parameetrid, viigiga: bool) -> tuple[float, float, float]:
    return en.tõenäosused(r_kodu, r_kyl, p) if viigiga else en.tõenäosused_kaks(r_kodu, r_kyl, p)


class Ulevaated:
    """Ehitab ühe läbimisega kõigi meeskonnamängude (tulemusega alad) tabeli kohad, meeskonnaajaloo ja lubatud aladel ennustused."""

    def __init__(self, events, teams: Teams, today: date) -> None:
        self.today = today
        recs: list[Rec] = []
        self.n_tulemusi: dict[str, int] = defaultdict(int)
        self.venue_games: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)   # (ala, koht) → [(võitja, id)] tulemusega mängud
        for e in sorted(events, key=lambda x: (x.start, x.id)):
            if e.sport in tul.RESULT_SPORTS and e.away:
                t = tul.parse(e.sport, e.result)
                recs.append(Rec(e.id, e.sport, e.league, e.level, hooaeg(e.sport, e.start.date()), e.start, teams.canonical(e.sport, e.home),
                                teams.canonical(e.sport, e.away), e.venue or "", t))
        self.recs = {r.id: r for r in recs}
        self.by_team: dict[tuple[str, str], list[Rec]] = defaultdict(list)
        for r in recs:
            self.by_team[(r.sport, r.kodu)].append(r)
            self.by_team[(r.sport, r.kyl)].append(r)
            if r.t:
                self.n_tulemusi[r.sport] += 1
                if r.venue:
                    self.venue_games[(r.sport, r.venue)].append((tul.voitja(r.t), r.id))
        self._walk(recs)

    def _walk(self, recs: list[Rec]) -> None:
        by_league: dict[tuple[str, str], list[Rec]] = defaultdict(list)
        for r in recs:
            by_league[(r.sport, r.liiga)].append(r)
        for (sport, _liiga), games in by_league.items():
            p = ENNUSTA.get(sport)
            rat: dict[str, float] = defaultdict(lambda: en.ALGUS)
            mange: dict[str, int] = defaultdict(int)
            pts: dict[str, int] = defaultdict(int)
            hoo = None
            for r in games:
                if hoo is not None and r.hooaeg != hoo:
                    if p:
                        en.taanda(rat, p.taandumine)
                    pts.clear()
                    mange.clear()
                hoo = r.hooaeg
                r.mange_enne = (mange[r.kodu], mange[r.kyl])
                if p and r.ennusta:
                    r.r_enne = (rat[r.kodu], rat[r.kyl])
                    r.pr = _toenaosused(*r.r_enne, p, r.viigiga)
                ranked = sorted((t for t in mange if mange[t] >= MIN_MANGE), key=lambda t: (-pts[t] / mange[t], -pts[t], t))
                if len(ranked) >= MIN_TABEL_MEESKONDI:
                    koht = {t: i + 1 for i, t in enumerate(ranked)}
                    r.tabel = {"meeskondi": len(ranked)}
                    for key, t in (("kodu", r.kodu), ("kyl", r.kyl)):
                        if t in koht:
                            r.tabel[key] = (koht[t], pts[t] / mange[t], mange[t])
                if r.t:
                    if p and r.ennusta:
                        w = en.tegelik(_Wrap(r.t))
                        s = {"kodu": 1.0, "viik": 0.5, "kylaline": 0.0}[w]
                        d = p.k * (s - (r.pr[0] + 0.5 * r.pr[1]))
                        rat[r.kodu] += d
                        rat[r.kyl] -= d
                        r.r_parast = (rat[r.kodu], rat[r.kyl])
                    kp, gp = tul.liigapunktid(sport, r.t)
                    pts[r.kodu] += kp
                    pts[r.kyl] += gp
                    mange[r.kodu] += 1
                    mange[r.kyl] += 1

    # ---- ülevaate osad ---------------------------------------------------------------------------------------------

    def _vorm(self, team: str, r: Rec, kaasa: bool = False) -> str | None:
        """Meeskonna viimased VORM mängu enne `r`-i (kaasa = ka `r` ise)."""
        seq = [x for x in self.by_team[(r.sport, team)] if x.t and (x.start <= r.start if kaasa else x.start < r.start)][-VORM:]
        if not seq:
            return None
        letters = [_voit(x.t, x.kodu == team) for x in seq]
        v, x_, k = letters.count("V"), letters.count("X"), letters.count("K")
        sc = sum((x.t.kodu if x.kodu == team else x.t.kylaline) for x in seq)
        gc = sum((x.t.kylaline if x.kodu == team else x.t.kodu) for x in seq)
        unit = tul.UNITS_PL[tul.UNITS[r.sport]]
        viik = f", {x_} viiki" if r.viigiga else ""
        return f"{team}: {' '.join(letters)} (viimased {len(seq)}: {v} võitu{viik}, {k} kaotust; {unit} {sc}:{gc})"

    def _omavahel(self, r: Rec) -> list[str]:
        out = []
        for x in self.by_team[(r.sport, r.kodu)]:
            if x.t and x.start < r.start and {x.kodu, x.kyl} == {r.kodu, r.kyl}:
                out.append(f"{_kp(x.start.date())}: {x.kodu} {x.t.tekst} {x.kyl} ({x.liiga})")
        return out[-OMAVAHELISI:]

    def _koht(self, r: Rec) -> list[str]:
        out = []
        if not r.venue:
            return out
        rows = [(w, i) for w, i in self.venue_games.get((r.sport, r.venue), []) if i != r.id and self.recs[i].start < r.start]
        n = len(rows)
        if n >= HALLI_MIN:
            kodu = sum(1 for w, _ in rows if w == "kodu")
            viik = sum(1 for w, _ in rows if w == "viik")
            viigid = f", viigiga lõppes {viik}" if r.viigiga else ""
            out.append(f"{r.venue}: andmestikus on {n} varasemat tulemusega mängu, neist võitis kodumeeskond {kodu}{viigid}, külaline võitis {n - kodu - viik}.")
        elif n:
            out.append(f"{r.venue}: andmestikus on sellest kohast {n} varasemat tulemusega mängu (statistikaks liiga vähe).")
        return out

    def _next(self, team: str, r: Rec) -> Rec | None:
        return next((x for x in self.by_team[(r.sport, team)] if x.start > r.start and x.id != r.id), None)

    def _jargmine(self, team: str, r: Rec) -> str | None:
        """Meeskonna järgmine mäng pärast `r`-i: vastane, aeg, tulemus; tõenäosus ainult siis, kui see mäng on lubatud ennustama."""
        nxt = self._next(team, r)
        if not nxt:
            return None
        kodus = nxt.kodu == team
        vastane = nxt.kyl if kodus else nxt.kodu
        kus = "kodus" if kodus else "võõrsil"
        pw = nxt.pr[0] if kodus else nxt.pr[2]
        if nxt.t:
            skoor = (nxt.t.kodu, nxt.t.kylaline) if kodus else (nxt.t.kylaline, nxt.t.kodu)
            kasv = f" (enne mängu andis mudel võiduks {_ph(pw)})" if nxt.ennusta else ""
            return f"{team}: {_kp(nxt.start.date())} {kus} vastu {vastane}, lõppes {skoor[0]}:{skoor[1]}{kasv}"
        kasv = f", mudeli hinnang võidule {_ph(pw)}" if nxt.ennusta else ""
        return f"{team}: {_kp(nxt.start.date())} {kus} vastu {vastane}{kasv}"

    def _jargmised(self, r: Rec) -> dict:
        nxt = [(t, self._jargmine(t, r), (self._next(t, r) or r).id) for t in (r.kodu, r.kyl)]
        nxt = [x for x in nxt if x[1]]
        return {"title": "Järgmised mängud", "items": [x[1] for x in nxt] or ["Järgmisi mänge andmestikus (veel) pole."], "ids": [x[2] for x in nxt]}

    def tabel(self, sport: str, liiga: str) -> dict | None:
        """Liigalehe „meie tabel“: võistkonnad meie mudeli tugevuse järgi (viimane hooaeg selles liigas) + arvutatud punktid ja vorm.
        Ainult alal ja tasemel, kus ennustus on lubatud (`ENNUSTA`, `ENNUSTUSE_TASEMED`); karikad, turniirid ja finaalid välja.
        Tugevuse ebakindlus ≈ 350/√mänge (ligikaudne: 36 mängu ±60); lähedased numbrid on praktiliselt võrdsed."""
        nimi = liiga.lower()
        if sport not in ENNUSTA or any(w in nimi for w in ("karikas", "turniir", "finaal")):
            return None
        games = [r for r in self.recs.values() if r.sport == sport and r.liiga == liiga and r.level in ENNUSTUSE_TASEMED and r.t]
        if not games:
            return None
        hoo = max(r.hooaeg for r in games)
        games = sorted((r for r in games if r.hooaeg == hoo), key=lambda r: (r.start, r.id))
        st: dict[str, dict] = defaultdict(lambda: {"m": 0, "v": 0, "x": 0, "k": 0, "gf": 0, "ga": 0, "pts": 0, "letters": [], "rating": en.ALGUS})
        for r in games:
            for team, kodus, rt in ((r.kodu, True, r.r_parast[0] if r.r_parast else None), (r.kyl, False, r.r_parast[1] if r.r_parast else None)):
                x = st[team]
                gf, ga = (r.t.kodu, r.t.kylaline) if kodus else (r.t.kylaline, r.t.kodu)
                letter = _voit(r.t, kodus)
                x["m"] += 1
                x["v"] += letter == "V"
                x["x"] += letter == "X"
                x["k"] += letter == "K"
                x["gf"] += gf
                x["ga"] += ga
                kp, gp = tul.liigapunktid(sport, r.t)
                x["pts"] += kp if kodus else gp
                x["letters"].append(letter)
                if rt is not None:
                    x["rating"] = rt
        by_pts = sorted(st, key=lambda t: (-st[t]["pts"], -(st[t]["gf"] - st[t]["ga"]), -st[t]["gf"], t))
        pts_rank = {t: i + 1 for i, t in enumerate(by_pts)}
        rows = []
        for i, t in enumerate(sorted(st, key=lambda t: (-st[t]["rating"], t)), 1):
            x = st[t]
            rows.append({"koht": i, "team": t, "tugevus": int(round(x["rating"] / 10.0)) * 10, "unc": int(round(350 / math.sqrt(x["m"]) / 10.0)) * 10,
                         "m": x["m"], "v": x["v"], "x": x["x"], "k": x["k"], "gf": x["gf"], "ga": x["ga"], "pts": x["pts"],
                         "pts_koht": pts_rank[t], "vorm": " ".join(x["letters"][-VORM:])})
        return {"hooaeg": hoo, "rows": rows, "viigiga": sport in tul.DRAWS, "yhik": tul.UNITS_PL[tul.UNITS[sport]], "mangud": len(games),
                "testimata": sport != "jalgpall", "n_tulemusi": self.n_tulemusi[sport]}

    def for_game(self, e) -> dict | None:
        """{"enne"|"parast": [{"title", "items"[, "ids"]}], "ennustus": bool, "meetod": str} või None, kui seda mängu ülevaade ei kata."""
        r = self.recs.get(e.id)
        if not r:
            return None
        if r.t:
            return self._parast(r)
        if r.start.date() < self.today:
            return None   # möödunud, tulemus puudub (nt edasi lükatud): ülevaadet ei näidata
        return self._enne(r)

    def _vorm_osa(self, r: Rec, kaasa: bool = False) -> dict | None:
        forms = [f for f in (self._vorm(r.kodu, r, kaasa), self._vorm(r.kyl, r, kaasa)) if f]
        if not forms:
            return None
        legend = "V võit, X viik, K kaotus" if r.viigiga else "V võit, K kaotus"
        return {"title": f"Vorm ({legend}{', kaasa arvatud see mäng' if kaasa else ''})", "items": forms}

    def _ennustus_osa(self, r: Rec) -> dict:
        ph, pv, pg = r.pr
        n1, n2 = r.mange_enne
        if min(n1, n2) < MIN_ENNUSTUS:
            return {"title": "Ennustus", "items": [
                f"Ennustust ei tee: selle liiga ({r.liiga}) andmetes on meeskondadel enne seda mängu {n1} ja {n2} tulemust, ennustuseks on vaja vähemalt {MIN_ENNUSTUS}."]}
        parts = [f"{r.kodu} võit {_ph(ph)}"] + ([f"viik {_ph(pv)}"] if r.viigiga else []) + [f"{r.kyl} võit {_ph(pg)}"]
        why = (f"Arvutus kasutab ainult andmestikus olevaid {r.liiga} tulemusi (kodumeeskonnal {n1}, külalisel {n2} mängu enne seda mängu) "
               f"ja kodueelist. See ei tea vigastustest, koosseisudest ega mängu tähtsusest.")
        if min(n1, n2) < 5:
            why += " Mõlema meeskonna tulemusi on veel vähe, seega on ennustus eriti ebakindel."
        if r.sport == "jalgpall":
            test = ("Tagasivaatavas testis (2026. hooaja jalgpalliliigad, iga mängu ennustus ainult varasemate tulemustega) oli Premium liigas täpsus umbes 59%, "
                    "sama mis tabelis kõrgemal oleva valimisel; tõenäosused olid täpsemad kui pikaajalised sagedused 8 liigas 8-st.")
        else:
            test = (f"Selle ala ennustust ei ole testitud: andmestikus on {self.n_tulemusi[r.sport]} tulemust, mis on liiga vähe, et täpsust mõõta. "
                    "Tõenäosused on seetõttu ainult ligikaudsed ja võivad olla eksitavad.")
        return {"title": "Meelelahutuslik ennustus", "items": ["Mudeli hinnang: " + "; ".join(parts) + ".", why, test,
                                                              "See on analüüs ja ei ole kihlveo nõuanne."]}

    def _enne(self, r: Rec) -> dict:
        sections = []
        if r.ennusta:
            sections.append(self._ennustus_osa(r))
        v = self._vorm_osa(r)
        if v:
            sections.append(v)
        tab = []
        for key, nimi in (("kodu", r.kodu), ("kyl", r.kyl)):
            if key in r.tabel:
                koht, ppg, m = r.tabel[key]
                tab.append(f"{nimi}: {koht}. koht {r.tabel['meeskondi']} meeskonnast ({f'{ppg:.2f}'.replace('.', ',')} punkti mängu kohta, {m} mängu).")
        if tab:
            sections.append({"title": "Arvutatud tabelikoht", "items": tab + [
                "Tabelit allikates pole: koht on arvutatud tulemustest hinnangulise punktisüsteemiga ja võib tegelikust erineda."]})
        oma = self._omavahel(r)
        sections.append({"title": "Omavahelised mängud", "items": oma or ["Andmestikus pole nende kahe omavahelisi mänge enne seda olnud."]})
        koht = self._koht(r)
        if koht:
            sections.append({"title": "Koht", "items": koht})
        return {"enne": sections, "parast": [], "ennustus": r.ennusta, "meetod": "Arvutatud tulemustest"}

    def _parast(self, r: Rec) -> dict:
        sections = []
        if r.ennusta:
            ph, pv, pg = r.pr
            w = en.tegelik(_Wrap(r.t))
            idx = {"kodu": 0, "viik": 1, "kylaline": 2}[w]
            p_act = r.pr[idx]
            fav = max(range(3), key=lambda i: r.pr[i])
            nimi = {0: f"{r.kodu} võit", 1: "viik", 2: f"{r.kyl} võit"}
            pidas = fav == idx
            if pidas:
                tase = "ootuspärane tulemus"
            elif p_act >= 0.30:
                tase = "väike üllatus"
            elif p_act >= 0.15:
                tase = "üllatus"
            else:
                tase = "suur üllatus"
            enne = f"{r.kodu} võit {_ph(ph)}" + (f", viik {_ph(pv)}" if r.viigiga else "") + f", {r.kyl} võit {_ph(pg)}"
            sections.append({"title": "Kas ennustus pidas?", "items": [
                f"Enne mängu andis mudel: {enne}.",
                f"Tulemus: {nimi[idx]} ({r.t.tekst}). Mudeli kõige tõenäolisem tulemus oli {nimi[fav]} ({_ph(r.pr[fav])}): ennustus {'pidas' if pidas else 'ei pidanud'}.",
                f"Selle tulemuse tõenäosus oli mudeli järgi {_ph(p_act)}: {tase}."]
                + ([] if r.sport == "jalgpall" else [f"Selle ala mudelit ei ole testitud: andmestikus on {self.n_tulemusi[r.sport]} tulemust, mis on liiga vähe täpsuse mõõtmiseks, "
                                                    "seega on hinnang ainult ligikaudne."])})
            if r.r_parast:
                d1, d2 = r.r_parast[0] - r.r_enne[0], r.r_parast[1] - r.r_enne[1]
                sections.append({"title": "Tugevusnumbri muutus", "items": [
                    f"{r.kodu}: {r.r_enne[0]:.0f} → {r.r_parast[0]:.0f} ({d1:+.0f}); {r.kyl}: {r.r_enne[1]:.0f} → {r.r_parast[1]:.0f} ({d2:+.0f}).",
                    "See on meie arvutatud tugevusnumber (algus 1500), mitte ametlik reiting; see muutub iga tulemusega."]})
        else:
            v = self._vorm_osa(r, kaasa=True)
            if v:
                sections.append(v)
            oma = self._omavahel(r)
            if oma:
                sections.append({"title": "Varasemad omavahelised mängud", "items": oma})
        sections.append(self._jargmised(r))
        return {"enne": [], "parast": sections, "ennustus": r.ennusta, "meetod": "Arvutatud tulemustest"}


class _Wrap:
    """`ennustus.tegelik` tahab objekti, millel on `.t`."""

    def __init__(self, t: tul.Tulemus) -> None:
        self.t = t
