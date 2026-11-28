"""Halli efekt: kui palju paremini mängib meeskond SAMAL hooajal ühes hallis kodus kui võõrsil (tema tugevus on nii kontrollitud).

Metoodika (versioon 2, ei ole avaldatud; avaldamine alles pärast ülevaatust):
- Iga (meeskond, hooaeg) kohta: võidu-% kodus ja võidu-% võõrsil (viik ei ole võit; viigid on eraldi veerg, jalgpallis lisaks punktid 3/1/0 mängu kohta).
- Halli efekt = Σ_meeskonnad kodumänge_hallis · (kodu-% hallis − sama meeskonna võõrsil-%) / Σ kodumänge_hallis, st kodu-% hallis miinus
  meeskondade võõrsil-% kaalutud nende kodumängude arvuga selles hallis.
- Mängud, mida ei arvestata: koondised (tase 5), turniirid/finaalid/karikas/eelhooaja mängud (võimalikud neutraalsed või rotatsioonilised väljakud),
  mängud, kus kodumeeskond pole halli tegelik kasutaja (vähem kui `MIN_KODU` kodumängu selles hallis samal hooajal), mängud tundmatus paigas.
- Meeskond läheb arvesse ainult siis, kui tal on samal hooajal vähemalt `MIN_VOORAS` võõrsilmängu tulemusega.
- Halli kohta: vähemalt `MIN_TULEMUSI` arvestatud kodumängu. Usaldusvahemik: Newcombe'i hübriidskoor kahe osakaalu vahele (Wilsoni piiridest);
  võõrsil osakaalu valim = nende meeskondade võõrsilmängude summa: ligikaudne, sest samad võõrsilmängud kordavad end mitmes hallis.
- **See ei ole põhjuslik seos**: efekt võib tuleda katet, valgustusest, publikust, reisist, ajakavast või väikese valimi juhusest.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from . import lood, tulemus as tul

MIN_TULEMUSI = 15       # arvestatud kodumänge hallis
MIN_KODU = 5            # meeskonna kodumänge selles hallis samal hooajal (muidu pole „tegelik kasutaja“)
MIN_VOORAS = 5          # meeskonna võõrsilmänge samal hooajal
LAHKUMINE_PP = 20.0     # raporti lävi
VALJA_SONAD = ("turniir", "finaal", "karikas", "pre-season", "europe cup", "maavõistlus", "super")


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """Wilsoni 95% vahemik osakaalule k/n (murruna 0..1)."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def newcombe(p1: float, n1: float, p2: float, n2: float) -> tuple[float, float]:
    """Newcombe'i hübriidskoor vahele p1 − p2 (95%), osakaalud murruna; tagastab (alla, üles) murruna."""
    l1, u1 = wilson(p1 * n1, n1)
    l2, u2 = wilson(p2 * n2, n2)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def valjajaetud(e) -> str:
    """Põhjus, miks mäng välja jäetakse, või tühi sõne."""
    if e.level == 5:
        return "koondis"
    nimi = e.league.lower()
    for s in VALJA_SONAD:
        if s in nimi:
            return f"turniir/karikas/eelhooaeg ({s})"
    return ""


@dataclass
class Mang:
    e: object
    t: tul.Tulemus
    kodu: str
    kylaline: str
    hoo: str
    paik: str | None


@dataclass
class MeeskondHallis:
    meeskond: str
    hoo: str
    kodu: list = field(default_factory=list)      # [(Mang, tulemus meeskonna vaates "V"/"X"/"K")]
    voorsil: list = field(default_factory=list)

    @staticmethod
    def _c(rows):
        v = sum(1 for _, r in rows if r == "V")
        x = sum(1 for _, r in rows if r == "X")
        return v, x, len(rows) - v - x

    @property
    def n_kodu(self) -> int:
        return len(self.kodu)

    @property
    def n_voor(self) -> int:
        return len(self.voorsil)


def _tulemus(m: Mang, kodu_poolt: bool) -> str:
    w = tul.voitja(m.t)
    if w == "viik":
        return "X"
    return "V" if (w == "kodu") == kodu_poolt else "K"


def koosta(events, paigad, teams) -> dict:
    """{"hallid": [...], "valjajaetud": {põhjus: arv}, "alus": {...}}. Iga halli kohta sõnastik, vt `_halli_rida`."""
    games: list[Mang] = []
    valja: dict[str, int] = defaultdict(int)
    for e in events:
        t = tul.parse(e.sport, e.result) if e.away else None
        if not t:
            continue
        why = valjajaetud(e)
        if why:
            valja[why] += 1
            continue
        p = paigad.paik_of(e.venue) if e.venue else None
        games.append(Mang(e, t, teams.canonical(e.sport, e.home), teams.canonical(e.sport, e.away),
                          lood.hooaeg(e.sport, e.start.date()), p.nimi if p else None))
    # meeskonna võõrsilmängud hooajal (kõik arvestatavad, mis tahes kohas)
    away: dict[tuple, list] = defaultdict(list)
    home: dict[tuple, list] = defaultdict(list)
    for m in games:
        away[(m.e.sport, m.kylaline, m.hoo)].append((m, _tulemus(m, False)))
        home[(m.e.sport, m.kodu, m.hoo)].append((m, _tulemus(m, True)))
    by_paik: dict[str, list[MeeskondHallis]] = defaultdict(list)
    kasutaja_valja = 0
    for (sport, team, hoo), rows in home.items():
        per: dict[str, list] = defaultdict(list)
        for m, r in rows:
            if m.paik:
                per[m.paik].append((m, r))
            else:
                valja["tundmatu paik"] += 1
        for paik, pr in per.items():
            if len(pr) < MIN_KODU:
                kasutaja_valja += len(pr)
                continue
            a = away.get((sport, team, hoo), [])
            if len(a) < MIN_VOORAS:
                valja[f"meeskonnal alla {MIN_VOORAS} võõrsilmängu"] += len(pr)
                continue
            by_paik[paik].append(MeeskondHallis(team, hoo, pr, a))
    if kasutaja_valja:
        valja[f"kodumeeskond pole halli tegelik kasutaja (alla {MIN_KODU} kodumängu hallis)"] += kasutaja_valja
    pmap = {p.nimi: p for p in paigad.paigad}
    hallid = [_halli_rida(paik, ms, pmap) for paik, ms in by_paik.items()]
    hallid.sort(key=lambda x: (-abs(x["efekt_pp"]) if x["n"] >= MIN_TULEMUSI else 0, -x["n"]))
    arv = [h for h in hallid if h["n"] >= MIN_TULEMUSI]
    tot_n = sum(h["n"] for h in arv)
    alus = {"hallid": len(arv), "kodumange": tot_n,
            "keskmine_efekt_pp": round(sum(h["efekt_pp"] * h["n"] for h in arv) / tot_n, 1) if tot_n else 0.0}
    return {"hallid": hallid, "valjajaetud": dict(valja), "alus": alus}


def _halli_rida(paik: str, ms: list[MeeskondHallis], pmap) -> dict:
    n = sum(m.n_kodu for m in ms)
    vh = sum(MeeskondHallis._c(m.kodu)[0] for m in ms)
    xh = sum(MeeskondHallis._c(m.kodu)[1] for m in ms)
    a_win = sum(m.n_kodu * MeeskondHallis._c(m.voorsil)[0] / m.n_voor for m in ms) / n
    a_draw = sum(m.n_kodu * MeeskondHallis._c(m.voorsil)[1] / m.n_voor for m in ms) / n
    ppg_h = (3 * vh + xh) / n
    ppg_a = sum(m.n_kodu * (3 * MeeskondHallis._c(m.voorsil)[0] + MeeskondHallis._c(m.voorsil)[1]) / m.n_voor for m in ms) / n
    n_away = sum(m.n_voor for m in ms)
    lo, hi = newcombe(vh / n, n, a_win, n_away)
    p = pmap.get(paik)
    return {"paik": paik, "linn": p.linn if p else "", "tapsus": p.tapsus if p else "", "n": n, "meeskondi": len(ms),
            "kodu_pct": round(100 * vh / n, 1), "kodu_viik_pct": round(100 * xh / n, 1),
            "voor_pct": round(100 * a_win, 1), "voor_viik_pct": round(100 * a_draw, 1),
            "efekt_pp": round(100 * (vh / n - a_win), 1), "lo": round(100 * lo, 1), "hi": round(100 * hi, 1),
            "ppg_efekt": round(ppg_h - ppg_a, 2), "meeskonnad": ms,
            "liigad": sorted({m.kodu[0][0].e.league for m in ms if m.kodu})}


# ---- raport (Markdown, ülevaatuseks; ei lähe lehele) ------------------------------------------------------------------

def _pp(x: float) -> str:
    return f"{x:+.1f}".replace(".", ",") + " pp"


def _kp(m: Mang) -> str:
    return m.e.start.strftime("%Y-%m-%d")


def raport(res: dict, nimed_otsi: tuple[str, ...] = ()) -> str:
    arv = [h for h in res["hallid"] if h["n"] >= MIN_TULEMUSI]
    flagged = [h for h in arv if abs(h["efekt_pp"]) > LAHKUMINE_PP]
    out = ["# Halli efekt: uus metoodika, ülevaatuse raport (ei ole avaldatud)", "",
           "Efekt = meeskonna kodu-% hallis miinus sama meeskonna võõrsil-% samal hooajal (võit; viik eraldi), kaalutud kodumängude arvuga hallis. "
           f"Valim: vähemalt {MIN_TULEMUSI} arvestatud kodumängu hallis; meeskonnal vähemalt {MIN_KODU} kodumängu selles hallis ja {MIN_VOORAS} võõrsilmängu. "
           "95% vahemik on Newcombe'i hübriidskoor (ligikaudne). **Ei ole põhjuslik seos.**", "",
           f"Arvesse läks {res['alus']['hallid']} halli ja {res['alus']['kodumange']} kodumängu. Kõigi hallide kaalutud keskmine efekt: **{_pp(res['alus']['keskmine_efekt_pp'])}** "
           "(see on tavaline kodueelis; halli enda mõju on lahkumine sellest).", "",
           "## Välja jäetud mängud", ""]
    for k, v in sorted(res["valjajaetud"].items(), key=lambda x: -x[1]):
        out.append(f"- {k}: {v}")
    out += ["", f"## Kõik hallid (vähemalt {MIN_TULEMUSI} mängu), efekti järgi", "",
            "| Koht | Mänge | Meeskondi | Kodu võit | Võõrsil võit | Efekt | 95% vahemik | Kodu viik / võõrsil viik | Punktid/mäng efekt | Asukoht |",
            "|---|---:|---:|---:|---:|---:|---|---|---:|---|"]
    for h in sorted(arv, key=lambda x: -x["efekt_pp"]):
        out.append(f"| {h['paik']}, {h['linn']} | {h['n']} | {h['meeskondi']} | {h['kodu_pct']:.0f}% | {h['voor_pct']:.0f}% | **{_pp(h['efekt_pp'])}** | "
                   f"{h['lo']:.0f} … {h['hi']:.0f} pp | {h['kodu_viik_pct']:.0f}% / {h['voor_viik_pct']:.0f}% | {_pp(h['ppg_efekt'] * 1).replace(' pp', '')} | {h['tapsus']} |")
    out += ["", f"## Toorandmed: hallid, kus |efekt| > {LAHKUMINE_PP:.0f} pp", ""]
    nimed = [h for h in res["hallid"] if h not in flagged and any(s.lower() in h["paik"].lower() for s in nimed_otsi)]
    for h in flagged + nimed:
        out += _toor(h, h in flagged, arv)
    leitud = {s for s in nimed_otsi if any(s.lower() in h["paik"].lower() for h in res["hallid"])}
    puudu = [s for s in nimed_otsi if s not in leitud]
    if puudu:
        out += ["## Soovitud kohad, mida arvutuses pole", ""]
        out += [f"- „{s}“: ühtegi sobivat halli ei jõudnud arvutusse (valim, välistus või nimi)." for s in puudu]
    return "\n".join(out)


def _toor(h: dict, lavi: bool, arv: list) -> list[str]:
    ok = h["n"] >= MIN_TULEMUSI
    pealkiri = f"### {h['paik']}, {h['linn']}: {_pp(h['efekt_pp'])}" + ("" if lavi else (" (alla läve" if ok else f" (valim {h['n']} < {MIN_TULEMUSI}") + ", soovitud koht)")
    out = [pealkiri, "",
           f"Arvestatud kodumänge {h['n']}, meeskondi {h['meeskondi']}, asukoha täpsus: {h['tapsus']}; liigad: {', '.join(h['liigad'])}. "
           f"Kodu võit {h['kodu_pct']:.0f}% vs sama meeskondade võõrsil {h['voor_pct']:.0f}% (95%: {h['lo']:.0f} … {h['hi']:.0f} pp); "
           f"viigid kodus {h['kodu_viik_pct']:.0f}% / võõrsil {h['voor_viik_pct']:.0f}%; punktid mängu kohta {_pp(h['ppg_efekt']).replace(' pp', '')}.", "",
           "| Meeskond | Hooaeg | Kodus selles hallis V-X-K | Kodu-% | Võõrsil (kõik hallid) V-X-K | Võõrsil-% | Vahe |", "|---|---|---|---:|---|---:|---:|"]
    for m in sorted(h["meeskonnad"], key=lambda x: -x.n_kodu):
        kv, kx, kk = MeeskondHallis._c(m.kodu)
        av, ax, ak = MeeskondHallis._c(m.voorsil)
        out.append(f"| {m.meeskond} | {m.hoo} | {m.n_kodu}: {kv}-{kx}-{kk} | {100 * kv / m.n_kodu:.0f}% | {m.n_voor}: {av}-{ax}-{ak} | {100 * av / m.n_voor:.0f}% | "
                   f"{_pp(100 * (kv / m.n_kodu - av / m.n_voor))} |")
    out += ["", "Kodumängud selles hallis (märgistus: KODU = kodumeeskond on halli kasutaja):", "", "| Kuupäev | Kodu (KODU) | Külaline | Tulemus | Liiga |", "|---|---|---|---|---|"]
    rows = sorted((g for m in h["meeskonnad"] for g, _ in m.kodu), key=lambda g: g.e.start)
    for g in rows:
        out.append(f"| {_kp(g)} | {g.kodu} (KODU) | {g.kylaline} | {g.t.kodu}:{g.t.kylaline} | {g.e.league} |")
    out += ["", "Meeskondade võõrsilmängud (võrdlusbaas):", ""]
    for m in sorted(h["meeskonnad"], key=lambda x: -x.n_kodu):
        out.append(f"- **{m.meeskond}** võõrsil: " + "; ".join(
            f"{_kp(g)} {g.kodu} {g.t.kodu}:{g.t.kylaline} ({r})" for g, r in sorted(m.voorsil, key=lambda x: x[0].e.start)))
    out.append("")
    return out


def main() -> None:
    import argparse
    from .andmed import load_events
    from .meeskonnad import Teams
    from .paigad import Paigad
    ap = argparse.ArgumentParser(description="Halli efekti ülevaatuse raport (Markdown stdout-i)")
    ap.add_argument("--koht", action="append", default=[], help="lisa raportisse kohad, mille nimes on see sõna (nt Wismari)")
    a = ap.parse_args()
    events = load_events()
    print(raport(koosta(events, Paigad.load(), Teams.load().fit(events)), tuple(a.koht)))


if __name__ == "__main__":
    main()
