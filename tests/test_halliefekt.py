"""Halli efekt (meeskonna kodu-% miinus võõrsil-%, samal hooajal): kontroll tugevuse suhtes, välistused, valim, vahemik."""
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from analuus import halliefekt as he
from analuus.meeskonnad import Teams
from analuus.paigad import Paigad
from scrapers.model import TALLINN, new_event

TOML = '''
[[paik]]
nimi = "Hall A"
linn = "Tallinn"
lat = 59.43
lon = 24.75
tapsus = "tapne"
kohad = ["Hall A"]

[[paik]]
nimi = "Hall B"
linn = "Tallinn"
lat = 59.40
lon = 24.70
tapsus = "tapne"
kohad = ["Hall B"]
'''
VENUES = '[[venue]]\nname = "Hall A"\ncity = "Tallinn"\n[[venue]]\nname = "Hall B"\ncity = "Tallinn"\n'


def paigad():
    d = Path(tempfile.mkdtemp())
    (d / "p.toml").write_text(TOML, encoding="utf-8")
    (d / "v.toml").write_text(VENUES, encoding="utf-8")
    return Paigad.load(d / "p.toml", d / "v.toml")


_n = [0]


def ev(home, away, result, venue, league="Liiga", level=1):
    _n[0] += 1
    d = date(2026, 4, 1) + timedelta(days=_n[0])
    return new_event(source="t", sport="jalgpall", league=league, start=datetime(d.year, d.month, d.day, 18, 0, tzinfo=TALLINN), home=home, away=away,
                     venue=venue, city="Tallinn", url="https://example.org/", result=result, level=level)


def run(events):
    return he.koosta(events, paigad(), Teams().fit(events))


def season(teams_home_wins, away_wins, hall="Hall A", n_home=8, n_away=6):
    """Iga meeskonna kohta n_home kodumängu hallis (wins võitu) ja n_away võõrsilmängu hallis B (wins võitu)."""
    out = []
    for team, (hw, aw) in {t: (teams_home_wins, away_wins) for t in ("X", "Y")}.items():
        for i in range(n_home):
            out.append(ev(team, "V" + team, "2-0" if i < hw else "0-1", hall))
        for i in range(n_away):
            out.append(ev("W" + team, team, "0-2" if i < aw else "1-0", "Hall B"))
    return out


class HalliEfektTest(unittest.TestCase):
    def hall(self, res, nimi="Hall A"):
        return next(h for h in res["hallid"] if h["paik"] == nimi)

    def test_strong_team_has_no_effect(self):
        # mõlemad meeskonnad võidavad kõik mängud, nii kodus kui võõrsil: kodu-% 100, võõrsil-% 100 → efekt 0 (tugevus kontrollitud)
        h = self.hall(run(season(8, 6)))
        self.assertEqual((h["n"], h["meeskondi"], h["kodu_pct"], h["voor_pct"], h["efekt_pp"]), (16, 2, 100.0, 100.0, 0.0))

    def test_home_effect_is_difference_to_own_away(self):
        h = self.hall(run(season(8, 3)))          # kodus 8/8, võõrsil 3/6 = 50%
        self.assertEqual((h["kodu_pct"], h["voor_pct"], h["efekt_pp"]), (100.0, 50.0, 50.0))
        self.assertLess(h["lo"], 50.0)
        self.assertGreater(h["hi"], 50.0)

    def test_small_sample_and_irregular_users_are_excluded(self):
        res = run(season(8, 3, n_home=4))          # 4 kodumängu < MIN_KODU → meeskond pole halli kasutaja
        self.assertFalse([h for h in res["hallid"] if h["paik"] == "Hall A"])
        self.assertTrue(any("tegelik kasutaja" in k for k in res["valjajaetud"]))
        res = run(season(8, 3, n_home=5))          # 10 kodumängu < MIN_TULEMUSI: rida on, aga valim jääb alla läve
        self.assertLess(self.hall(res)["n"], he.MIN_TULEMUSI)

    def test_tournaments_koondised_and_few_away_games_are_excluded(self):
        evs = season(8, 3)
        n0 = self.hall(run(evs))["n"]
        extra = [ev("X", "Z", "1-0", "Hall A", league="Balti turniir") for _ in range(5)]
        extra += [ev("X", "Z", "1-0", "Hall A", level=5) for _ in range(5)]
        res = run(evs + extra)
        self.assertEqual(self.hall(res)["n"], n0)
        self.assertEqual(res["valjajaetud"]["koondis"], 5)
        res = run(season(8, 3, n_away=4))          # alla 5 võõrsilmängu → meeskonda ei arvestata
        self.assertFalse([h for h in res["hallid"] if h["paik"] == "Hall A"])

    def test_draws_are_separate_not_wins(self):
        evs = [ev("X", "VX", "1-1", "Hall A") for _ in range(8)] + [ev("Y", "VY", "1-1", "Hall A") for _ in range(8)]
        for t in ("X", "Y"):
            evs += [ev("W" + t, t, "1-0", "Hall B") for _ in range(6)]
        h = self.hall(run(evs))
        self.assertEqual((h["kodu_pct"], h["kodu_viik_pct"], h["voor_pct"]), (0.0, 100.0, 0.0))

    def test_intervals(self):
        lo, hi = he.wilson(50, 100)
        self.assertAlmostEqual(lo, 0.404, delta=0.002)
        self.assertAlmostEqual(hi, 0.596, delta=0.002)
        lo, hi = he.newcombe(0.6, 100, 0.4, 100)
        self.assertLess(lo, 0.2)
        self.assertGreater(hi, 0.2)
        self.assertGreater(lo, 0.0)                 # 60% vs 40% sajast: nulli ei kata

    def test_report_lists_raw_games_for_flagged_halls(self):
        res = run(season(8, 0))                     # efekt +100 pp → üle läve
        md = he.raport(res)
        self.assertIn("### Hall A", md)
        self.assertIn("(KODU)", md)
        self.assertIn("Ei ole põhjuslik", md)


if __name__ == "__main__":
    unittest.main()
