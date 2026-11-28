"""Tagasivaatav test: Elo vs võrdlusalused. Ei avalda midagi, trükib Markdown-raporti.

    python -m analuus.tagasivaatav                 # Premium liiga, parameetrid valitud teistel liigadel
    python -m analuus.tagasivaatav --liiga "Esiliiga"

Ausus: testitava liiga mänge ei kasutata parameetrite valikul; iga mängu ennustus kasutab ainult varasemaid mänge.
"""

from __future__ import annotations

import argparse

from . import ennustus as en
from . import lood
from .andmed import load_events
from .meeskonnad import Teams

MIN_MANGE_LIIGAS = 80   # häälestusliigad: vähemalt nii palju mänge (muidu müra)
VAHELE = 5              # „soojenduse“ järel: mõlemal meeskonnal vähemalt nii mitu mängu enne


def _tabel(rows: list[tuple]) -> str:
    """Brier ja log-kaotus ainult tõenäosuslikel mudelitel (kõva valiku „1 või 0“ puhul pole need õiglased: eksimus = suurim võimalik karistus)."""
    out = ["| | Mänge | Täpsus | Brier | Log-kaotus |", "|---|---:|---:|---:|---:|"]
    for nimi, r, toenaosuslik in rows:
        b = f"{r['brier']:.3f}" if r.get("n") else "–"
        ll = f"{r['logloss']:.3f}" if toenaosuslik else "–"
        out.append(f"| {nimi} | {r['n']} | {r['tapsus'] * 100:.1f}% | {b} | {ll} |")
    return "\n".join(out)


def testi(grupid: dict, liiga: str, hooaeg: str) -> dict:
    test = grupid[(liiga, hooaeg)]
    treening = [g for (l, h), g in grupid.items() if l != liiga and len(g) >= MIN_MANGE_LIIGAS and lood.usaldusvaarne(g)]
    p, treeningu_brier = en.haalesta(treening, vahele=0)
    sag = en.sagedused([m for g in treening for m in g])

    elo = list(en.kaiguta(test, p))
    tabel = list(en.tabeli_ennustus(test))
    one_hot = {"kodu": (1.0, 0.0, 0.0), "kylaline": (0.0, 0.0, 1.0)}
    res = {"parameetrid": p, "treeningu_brier": treeningu_brier, "treening_liigu": len(treening),
           "treening_mange": sum(len(g) for g in treening), "sagedused": sag, "n": len(test)}
    for nimi, vahele in (("koik", 0), ("alates", VAHELE)):
        sel_e = [(pr, w) for m, pr, w, a, b in elo if a >= vahele and b >= vahele]
        sel_t = [(one_hot[v], w) for m, v, w, a, b in tabel if a >= vahele and b >= vahele]
        sel_h = [((1.0, 0.0, 0.0), w) for m, pr, w, a, b in elo if a >= vahele and b >= vahele]
        sel_k = [(sag, w) for m, pr, w, a, b in elo if a >= vahele and b >= vahele]
        res[nimi] = {"elo": en.hinda(sel_e), "tabel": en.hinda(sel_t), "kodu": en.hinda(sel_h), "sagedus": en.hinda(sel_k)}
        res[nimi]["rows_elo"] = sel_e
        res[nimi]["brier_elo"] = [en.brier(p_, w) for p_, w in sel_e]
        res[nimi]["brier_tabel"] = [en.brier(p_, w) for p_, w in sel_t]
        res[nimi]["brier_sagedus"] = [en.brier(p_, w) for p_, w in sel_k]
    return res


def raport(ms, liiga: str, hooaeg: str) -> str:
    grupid = en.liigad(ms)
    if (liiga, hooaeg) not in grupid:
        raise SystemExit(f"Liigat {liiga!r} hooajal {hooaeg} ei leitud")
    r = testi(grupid, liiga, hooaeg)
    p = r["parameetrid"]
    sag = r["sagedused"]
    out = [f"# Elo tagasivaatav test: {liiga} {hooaeg}", "",
           f"Testitud mänge: **{r['n']}**. Parameetrid valitud **teistel** liigadel ({r['treening_liigu']} liigat, {r['treening_mange']} mängu): "
           f"K = {p.k:g}, kodueelis = {p.kodueelis:g}, viigi parameeter c = {p.c:g} (testliiga andmeid ei kasutatud). "
           f"Tulemuste jaotus häälestusliigades: kodu {sag[0]*100:.0f}% / viik {sag[1]*100:.0f}% / külaline {sag[2]*100:.0f}%.", ""]
    for nimi, kirjeldus in (("koik", "Kõik mängud"), ("alates", f"Alates mängust, kus mõlemal meeskonnal on vähemalt {VAHELE} mängu enne")):
        d = r[nimi]
        out += [f"## {kirjeldus}", "", _tabel([("**Elo**", d["elo"], True), ("Tabelis kõrgemal võidab (kõva valik)", d["tabel"], False),
                                              ("Kodu võidab alati (kõva valik)", d["kodu"], False),
                                              ("Pikaajaline sagedus (kodu/viik/külaline)", d["sagedus"], True)]), ""]
        m, lo, hi = en.bootstrap_vahe(d["brier_elo"], d["brier_sagedus"])
        out.append(f"Brier, Elo miinus pikaajaline sagedus: **{m:+.3f}** (95% vahemik {lo:+.3f} … {hi:+.3f}; negatiivne = Elo parem).")
        m, lo, hi = en.bootstrap_vahe(d["brier_elo"], d["brier_tabel"])
        out.append(f"Brier, Elo miinus tabeli valik: **{m:+.3f}** (95% vahemik {lo:+.3f} … {hi:+.3f}).")
        out.append("")
    out += ["## Kalibratsioon (kodu võidu tõenäosus, alates soojendusest)", "",
            "| Ennustatud | Mänge | Ennustatud keskmine | Tegelik osakaal |", "|---|---:|---:|---:|"]
    for k in en.kalibratsioon(r["alates"]["rows_elo"], bins=5):
        out.append(f"| {k['alates']*100:.0f}–{k['kuni']*100:.0f}% | {k['n']} | {k['ennustatud']*100:.1f}% | {k['tegelik']*100:.1f}% |")
    out += ["", "Märkused: Brier on kolme tulemuse ruutviga (0 = täiuslik; sama jaotuse pakkumine kõigile ≈ 0,6). Täpsus = kõrgeima tõenäosusega tulemus; viiki Elo "
            "sisuliselt kunagi esikohale ei pane, seega täpsus ja Brier ütlevad eri asju. Andmetes on ainult üks hooaeg (2026), hooaja vahetust ei testita."]
    return "\n".join(out)


def leave_one_out(ms) -> str:
    """Kontroll: iga suur liiga korda testina, teised häälestuseks."""
    grupid = en.liigad(ms)
    suured = sorted(((k, g) for k, g in grupid.items() if len(g) >= MIN_MANGE_LIIGAS and lood.usaldusvaarne(g)), key=lambda x: -len(x[1]))[:8]
    out = ["| Liiga | Mänge | Elo Brier | Sagedus Brier | Tabel Brier | Elo täpsus | Tabel täpsus | Kodu täpsus |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    võidud = 0
    for (liiga, hoo), g in suured:
        d = testi(grupid, liiga, hoo)["alates"]
        out.append(f"| {liiga} | {d['elo']['n']} | {d['elo']['brier']:.3f} | {d['sagedus']['brier']:.3f} | {d['tabel']['brier']:.3f} | "
                   f"{d['elo']['tapsus']*100:.1f}% | {d['tabel']['tapsus']*100:.1f}% | {d['kodu']['tapsus']*100:.1f}% |")
        võidud += d["elo"]["brier"] < d["sagedus"]["brier"]
    out.append(f"\nElo Brier on pikaajalisest sagedusest parem {võidud}/{len(suured)} liigas.")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--liiga", default="Premium liiga")
    ap.add_argument("--hooaeg", default="2026")
    ap.add_argument("--kontroll", action="store_true", help="lisa: iga suur liiga korda testina")
    a = ap.parse_args()
    ms = lood.mangud(load_events(), Teams.load() if hasattr(Teams, "load") else Teams())
    print(raport(ms, a.liiga, a.hooaeg))
    if a.kontroll:
        print("\n## Kontroll: iga suur liiga korda testina (alates soojendusest)\n")
        print(leave_one_out(ms))


if __name__ == "__main__":
    main()
