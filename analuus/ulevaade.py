"""Mängu lehe automaatne ülevaade (enne ja pärast mängu).

Kõik read on arvutatud andmestikus olevatest tulemustest, kohtadest ja ülekannetest: vigastusi, koosseise, taustalugusid ega piletiandmeid
siin ei ole ega väljamõelda. Ülevaade ei ole tehisintellekti (keelemudeli) kirjutatud, vaid reeglipõhine tekst, mis tuleb samadest andmetest
igal ehitusel ühtmoodi. Ennustus on meelelahutuslik analüüs (Elo-tüüpi tugevusnumber, vt `ennustus.py`), mitte soovitus.

Ennustus ja vorm on praegu ainult jalgpallil (ainus ala, kus on tulemusi piisavalt; vt `tagasivaatav.py`). Muudel aladel on ainult koha ja
ülekande rida.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from . import ennustus as en
from . import tulemus as tul
from .lood import MIN_MANGE, hooaeg
from .meeskonnad import Teams

# Elo parameetrid: häälestusliigad (kõik teised liigad kui testitav) valisid K = 80; tundlikkuse kontroll näitas Brier skoori lamedat
# platood K = 60…120 juures, seega võetud on platoo vasak äär (K = 60, kõige väiksem muutus, mis on <1% parimast). Kodueelis 60, viigi c 0,3.
PARAMS = en.Parameetrid(k=60.0, kodueelis=60.0, c=0.3, taandumine=0.33)
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
    liiga: str
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


def _voit(t: tul.Tulemus, kodu_poolt: bool) -> str:
    """V = võit, X = viik, K = kaotus meeskonna vaates."""
    w = tul.voitja(t)
    if w == "viik":
        return "X"
    return "V" if (w == "kodu") == kodu_poolt else "K"


class Ulevaated:
    """Ehitab ühe läbimisega kõigi jalgpallimängude ennustused, tabeli kohad ja meeskonnaajaloo."""

    def __init__(self, events, teams: Teams, today: date, params: en.Parameetrid = PARAMS) -> None:
        self.today = today
        self.p = params
        recs: list[Rec] = []
        self.venue_games: dict[str, list[tuple[str, str]]] = defaultdict(list)   # koht → [(võitja, id)] tulemusega mängud
        for e in sorted(events, key=lambda x: (x.start, x.id)):
            if e.sport == "jalgpall" and e.away:
                t = tul.parse(e.sport, e.result)
                recs.append(Rec(e.id, e.league, hooaeg(e.sport, e.start.date()), e.start, teams.canonical(e.sport, e.home),
                                teams.canonical(e.sport, e.away), e.venue or "", t))
        self.recs = {r.id: r for r in recs}
        self.by_team: dict[str, list[Rec]] = defaultdict(list)
        for r in recs:
            self.by_team[r.kodu].append(r)
            self.by_team[r.kyl].append(r)
            if r.t and r.venue:
                self.venue_games[r.venue].append((tul.voitja(r.t), r.id))
        self._walk(recs)

    def _walk(self, recs: list[Rec]) -> None:
        by_league: dict[str, list[Rec]] = defaultdict(list)
        for r in recs:
            by_league[r.liiga].append(r)
        for games in by_league.values():
            rat: dict[str, float] = defaultdict(lambda: en.ALGUS)
            mange: dict[str, int] = defaultdict(int)
            pts: dict[str, int] = defaultdict(int)
            hoo = None
            for r in games:
                if hoo is not None and r.hooaeg != hoo:
                    en.taanda(rat, self.p.taandumine)
                    pts.clear()
                    mange.clear()
                hoo = r.hooaeg
                r.r_enne = (rat[r.kodu], rat[r.kyl])
                r.mange_enne = (mange[r.kodu], mange[r.kyl])
                r.pr = en.tõenäosused(*r.r_enne, self.p)
                ranked = sorted((t for t in mange if mange[t] >= MIN_MANGE), key=lambda t: (-pts[t] / mange[t], -pts[t], t))
                if len(ranked) >= MIN_TABEL_MEESKONDI:
                    koht = {t: i + 1 for i, t in enumerate(ranked)}
                    r.tabel = {"meeskondi": len(ranked)}
                    for key, t in (("kodu", r.kodu), ("kyl", r.kyl)):
                        if t in koht:
                            r.tabel[key] = (koht[t], pts[t] / mange[t], mange[t])
                if r.t:
                    w = en.tegelik(_Wrap(r.t))
                    s = {"kodu": 1.0, "viik": 0.5, "kylaline": 0.0}[w]
                    d = self.p.k * (s - (r.pr[0] + 0.5 * r.pr[1]))
                    rat[r.kodu] += d
                    rat[r.kyl] -= d
                    kp, gp = tul.liigapunktid("jalgpall", r.t)
                    pts[r.kodu] += kp
                    pts[r.kyl] += gp
                    mange[r.kodu] += 1
                    mange[r.kyl] += 1
                    r.r_parast = (rat[r.kodu], rat[r.kyl])

    # ---- ülevaate osad ---------------------------------------------------------------------------------------------

    def _vorm(self, team: str, r: Rec) -> str | None:
        seq = [x for x in self.by_team[team] if x.t and x.start < r.start][-VORM:]
        if not seq:
            return None
        letters = [_voit(x.t, x.kodu == team) for x in seq]
        v, x_, k = letters.count("V"), letters.count("X"), letters.count("K")
        nl = []
        for x in seq:
            skoor_oma, skoor_vas = (x.t.kodu, x.t.kylaline) if x.kodu == team else (x.t.kylaline, x.t.kodu)
            nl.append((skoor_oma, skoor_vas))
        sc = sum(a for a, _ in nl)
        gc = sum(b for _, b in nl)
        return (f"{team}: {' '.join(letters)} (viimased {len(seq)}: {v} võitu, {x_} viiki, {k} kaotust; väravaid {sc}:{gc})")

    def _omavahel(self, r: Rec) -> list[str]:
        out = []
        for x in self.by_team[r.kodu]:
            if x.t and x.start < r.start and {x.kodu, x.kyl} == {r.kodu, r.kyl}:
                out.append(f"{_kp(x.start.date())}: {x.kodu} {x.t.kodu}:{x.t.kylaline} {x.kyl} ({x.liiga})")
        return out[-OMAVAHELISI:]

    def _koht(self, r: Rec) -> list[str]:
        out = []
        if not r.venue:
            return out
        rows = [(w, i) for w, i in self.venue_games.get(r.venue, []) if i != r.id and self.recs[i].start < r.start]
        n = len(rows)
        if n >= HALLI_MIN:
            kodu = sum(1 for w, _ in rows if w == "kodu")
            viik = sum(1 for w, _ in rows if w == "viik")
            out.append(f"{r.venue}: andmestikus on {n} varasemat tulemusega mängu, neist võitis kodumeeskond {kodu}, viigiga lõppes {viik}, külaline võitis {n - kodu - viik}.")
        elif n:
            out.append(f"{r.venue}: andmestikus on sellest kohast {n} varasemat tulemusega mängu (statistikaks liiga vähe).")
        return out

    def _jargmine(self, team: str, r: Rec) -> str | None:
        """Meeskonna järgmine mäng pärast `r`-i: vastane, aeg, tõenäosus (selle mängu hetkel arvutatud) või tulemus."""
        nxt = next((x for x in self.by_team[team] if x.start > r.start and x.id != r.id), None)
        if not nxt:
            return None
        kodus = nxt.kodu == team
        vastane = nxt.kyl if kodus else nxt.kodu
        pw = nxt.pr[0] if kodus else nxt.pr[2]
        kus = "kodus" if kodus else "võõrsil"
        if nxt.t:
            skoor = (nxt.t.kodu, nxt.t.kylaline) if kodus else (nxt.t.kylaline, nxt.t.kodu)
            return f"{team}: {_kp(nxt.start.date())} {kus} vastu {vastane}, lõppes {skoor[0]}:{skoor[1]} (enne mängu andis mudel võiduks {_ph(pw)})"
        return f"{team}: {_kp(nxt.start.date())} {kus} vastu {vastane}, mudeli järgi võidu tõenäosus {_ph(pw)}"

    def _jargmine_id(self, team: str, r: Rec) -> str | None:
        nxt = next((x for x in self.by_team[team] if x.start > r.start and x.id != r.id), None)
        return nxt.id if nxt else None

    def for_game(self, e) -> dict | None:
        """{"enne"|"parast": [{"title", "items"[, "links"]}], "meetod": str, "viik": bool} või None, kui seda mängu ülevaade ei kata."""
        r = self.recs.get(e.id)
        if not r or e.sport != "jalgpall":
            return None
        if r.t:
            return self._parast(r)
        if r.start.date() < self.today:
            return None   # möödunud, tulemus puudub (nt edasi lükatud): ennustust ei näidata
        return self._enne(r)

    def _enne(self, r: Rec) -> dict:
        ph, pv, pg = r.pr
        n1, n2 = r.mange_enne
        sections = []
        if min(n1, n2) >= MIN_ENNUSTUS:
            prog = [f"{r.kodu} võidab: {_ph(ph)}", f"viik: {_ph(pv)}", f"{r.kyl} võidab: {_ph(pg)}"]
            why = (f"Arvutus kasutab ainult andmestikus olevaid {r.liiga} tulemusi (kodumeeskonnal {n1}, külalisel {n2} mängu enne seda mängu) "
                   f"ja kodueelist. See ei tea vigastustest, koosseisudest ega mängu tähtsusest.")
            if min(n1, n2) < 5:
                why += " Mõlema meeskonna tulemusi on veel vähe, seega on ennustus eriti ebakindel."
            sections.append({"title": "Meelelahutuslik ennustus", "items": [
                "; ".join(prog) + ".", why,
                "Tagasivaatavas testis (2026. hooaja jalgpalliliigad, iga mängu ennustus ainult varasemate tulemustega) oli Premium liigas täpsus umbes 59%, "
                "sama mis tabelis kõrgemal oleva valimisel; tõenäosused olid täpsemad kui pikaajalised sagedused 8 liigas 8-st."]})
        else:
            sections.append({"title": "Ennustus", "items": [
                f"Ennustust ei tee: selle liiga ({r.liiga}) andmetes on meeskondadel enne seda mängu {n1} ja {n2} tulemust, ennustuseks on vaja vähemalt {MIN_ENNUSTUS}."]})
        forms = [f for f in (self._vorm(r.kodu, r), self._vorm(r.kyl, r)) if f]
        if forms:
            sections.append({"title": "Vorm (V võit, X viik, K kaotus)", "items": forms})
        tab = []
        for key, nimi in (("kodu", r.kodu), ("kyl", r.kyl)):
            if key in r.tabel:
                koht, ppg, m = r.tabel[key]
                tab.append(f"{nimi}: {koht}. koht {r.tabel['meeskondi']} meeskonnast ({f'{ppg:.2f}'.replace('.', ',')} punkti mängu kohta, {m} mängu).")
        if tab:
            sections.append({"title": "Arvutatud tabelikoht", "items": tab + ["Tabelit allikates pole: koht on arvutatud tulemustest (võit 3, viik 1) ja võib tegelikust erineda."]})
        oma = self._omavahel(r)
        sections.append({"title": "Omavahelised mängud", "items": oma or ["Andmestikus (2026. hooaeg) pole nende kahe omavahelisi mänge enne seda olnud."]})
        koht = self._koht(r)
        if koht:
            sections.append({"title": "Koht", "items": koht})
        return {"enne": sections, "parast": [], "meetod": "Arvutatud tulemustest"}

    def _parast(self, r: Rec) -> dict:
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
        items = [f"Enne mängu andis mudel: {r.kodu} võidab {_ph(ph)}, viik {_ph(pv)}, {r.kyl} võidab {_ph(pg)}.",
                 f"Tulemus: {nimi[idx]} ({r.t.kodu}:{r.t.kylaline}). Mudeli kõige tõenäolisem tulemus oli {nimi[fav]} ({_ph(r.pr[fav])}): ennustus {'pidas' if pidas else 'ei pidanud'}.",
                 f"Selle tulemuse tõenäosus oli mudeli järgi {_ph(p_act)}: {tase}."]
        sections = [{"title": "Kas ennustus pidas?", "items": items}]
        if r.r_parast:
            d1, d2 = r.r_parast[0] - r.r_enne[0], r.r_parast[1] - r.r_enne[1]
            sections.append({"title": "Tugevusnumbri muutus", "items": [
                f"{r.kodu}: {r.r_enne[0]:.0f} → {r.r_parast[0]:.0f} ({d1:+.0f}); {r.kyl}: {r.r_enne[1]:.0f} → {r.r_parast[1]:.0f} ({d2:+.0f}).",
                "See on meie arvutatud tugevusnumber (algus 1500), mitte ametlik reiting; see muutub iga tulemusega."]})
        nxt = [(t, self._jargmine(t, r), self._jargmine_id(t, r)) for t in (r.kodu, r.kyl)]
        nxt = [x for x in nxt if x[1]]
        sections.append({"title": "Järgmised mängud", "items": [x[1] for x in nxt] or ["Järgmisi mänge andmestikus (veel) pole."],
                         "ids": [x[2] for x in nxt]})
        return {"enne": [], "parast": sections, "meetod": "Arvutatud tulemustest"}


class _Wrap:
    """`ennustus.tegelik` tahab objekti, millel on `.t`."""

    def __init__(self, t: tul.Tulemus) -> None:
        self.t = t
