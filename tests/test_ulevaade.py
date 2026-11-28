import unittest
from datetime import date, datetime

from analuus.meeskonnad import Teams
from analuus.ulevaade import Ulevaated
from scrapers.model import TALLINN, Event

TODAY = date(2026, 6, 1)


def ev(i, kodu, kyl, tulemus="", day=1, liiga="Premium liiga", sport="jalgpall", venue="Staadion"):
    return Event(id=f"e{i}", sport=sport, league=liiga, start=datetime(2026, 3, day, 18, 0, tzinfo=TALLINN), home=kodu, away=kyl,
                 venue=venue, city="Tallinn", url="https://x", source="t", result=tulemus)


def liiga(extra=()):
    """8 meeskonda, ringmängud: A tugev, H nõrk; siis tulevane mäng."""
    teams = list("ABCDEFGH")
    games, i, day = [], 0, 1
    for k in range(3):
        for a in teams:
            for b in teams:
                if a < b and (hash((a, b, k)) % 2 == 0):
                    i += 1
                    day = 1 + i % 25
                    tul = f"{3 if a == 'A' else 1}-{0 if a == 'A' else 1}" if "A" in (a, b) and a == "A" else ("0-2" if b == "A" else "1-1")
                    games.append(ev(i, a, b, tul, day))
    return games + list(extra)


class UlevaadeTest(unittest.TestCase):
    def build(self, events):
        return Ulevaated(events, Teams().fit(events), TODAY)

    def test_enne_mangu_on_tõenäosused_ja_andmeallikas(self):
        future = ev(900, "A", "H", "", day=28)
        future = Event(**{**future.__dict__, "start": datetime(2026, 7, 1, 18, tzinfo=TALLINN)})
        u = self.build(liiga([future])).for_game(future)
        self.assertTrue(u["enne"])
        txt = " ".join(i for s in u["enne"] for i in s["items"])
        self.assertIn("võidab", txt)
        self.assertIn("ei tea vigastustest", txt)
        self.assertNotIn("kihlvedu", txt.lower())

    def test_ennustus_ei_kasuta_mängu_enda_tulemust(self):
        base = liiga()
        g1 = ev(901, "A", "H", "0-5", day=27)
        g2 = ev(901, "A", "H", "5-0", day=27)
        a = self.build(base + [g1]).recs["e901"].pr
        b = self.build(base + [g2]).recs["e901"].pr
        self.assertEqual(a, b)

    def test_liiga_andmeteta_mangul_ennustust_pole(self):
        e = ev(950, "X", "Y", "", day=28, liiga="Uus turniir")
        e = Event(**{**e.__dict__, "start": datetime(2026, 7, 1, 18, tzinfo=TALLINN)})
        u = self.build([e]).for_game(e)
        txt = " ".join(i for s in u["enne"] for i in s["items"])
        self.assertIn("Ennustust ei tee", txt)
        self.assertNotIn("võidab:", txt)

    def test_parast_mangu_ennustuse_hinnang_ja_reitingu_muutus(self):
        base = liiga()
        done = ev(960, "H", "A", "2-0", day=27)   # nõrk võidab tugevat
        u = self.build(base + [done]).for_game(done)
        titles = [s["title"] for s in u["parast"]]
        self.assertEqual(titles[:2], ["Kas ennustus pidas?", "Tugevusnumbri muutus"])
        txt = " ".join(i for s in u["parast"] for i in s["items"])
        self.assertIn("ei pidanud", txt)
        self.assertIn("üllatus", txt)

    def test_muud_alad_ja_edasilukatud_mangud_ei_saa_ulevaadet(self):
        k = ev(970, "A", "B", "80-70", sport="korvpall")
        self.assertIsNone(self.build([k]).for_game(k))
        postponed = ev(971, "A", "B", "", day=2)   # möödunud, tulemust pole
        self.assertIsNone(self.build(liiga([postponed])).for_game(postponed))


if __name__ == "__main__":
    unittest.main()
