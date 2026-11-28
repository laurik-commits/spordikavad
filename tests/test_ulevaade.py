import unittest
from datetime import date, datetime

from analuus.meeskonnad import Teams
from analuus.ulevaade import Ulevaated
from scrapers.model import TALLINN, Event

TODAY = date(2026, 6, 1)


def ev(i, kodu, kyl, tulemus="", day=1, liiga="Premium liiga", sport="jalgpall", venue="Staadion", level=1):
    return Event(id=f"e{i}", sport=sport, league=liiga, start=datetime(2026, 3, day, 18, 0, tzinfo=TALLINN), home=kodu, away=kyl,
                 venue=venue, city="Tallinn", url="https://x", source="t", result=tulemus, level=level)


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
        self.assertIn("Mudeli hinnang", txt)
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

    def test_edasilukatud_mang_ei_saa_ulevaadet(self):
        postponed = ev(971, "A", "B", "", day=2)   # möödunud, tulemust pole
        self.assertIsNone(self.build(liiga([postponed])).for_game(postponed))

    def test_tasemed_3_4_5_saavad_ainult_fakte_ilma_tõenäosusteta(self):
        for lvl in (3, 4, 5):
            base = [ev(i + 1000, a, b, t, day=1 + i % 25, level=lvl) for i, (a, b, t) in enumerate(
                [(a, b, "2-0") for a in "ABCDEFGH" for b in "ABCDEFGH" if a < b])]
            fut = Event(**{**ev(990, "A", "H", "", level=lvl).__dict__, "start": datetime(2026, 7, 1, 18, tzinfo=TALLINN)})
            u = self.build(base + [fut]).for_game(fut)
            txt = " ".join(i for s in u["enne"] for i in s["items"])
            self.assertFalse(u["ennustus"])
            self.assertNotIn("%", txt.replace("100%", ""), lvl)                      # ühtegi tõenäosust
            self.assertNotIn("Ennustus", " ".join(s["title"] for s in u["enne"]))
            self.assertTrue(any(s["title"].startswith("Vorm") for s in u["enne"]))
            done = base[0]
            up = self.build(base + [fut]).for_game(done)
            titles = [s["title"] for s in up["parast"]]
            self.assertNotIn("Kas ennustus pidas?", titles)                          # ka pärast mängu mudelit ei näidata
            self.assertNotIn("Tugevusnumbri muutus", titles)
            self.assertNotIn("mudeli", " ".join(i for s in up["parast"] for i in s["items"]).lower())

    def test_tase_2_saab_ennustuse(self):
        fut = Event(**{**ev(991, "A", "H", "", level=2).__dict__, "start": datetime(2026, 7, 1, 18, tzinfo=TALLINN)})
        base = [Event(**{**e.__dict__, "level": 2}) for e in liiga()]
        u = self.build(base + [fut]).for_game(fut)
        self.assertTrue(u["ennustus"])
        self.assertIn("Mudeli hinnang", " ".join(i for s in u["enne"] for i in s["items"]))

    def test_vorkpall_on_kahe_tulemusega_ja_selgitab_testimatust(self):
        base = []
        i = 0
        for _ in range(2):
            for a in "ABCD":
                for b in "ABCD":
                    if a != b:
                        i += 1
                        base.append(ev(2000 + i, a, b, "3-0" if a == "A" else "0-3" if b == "A" else "3-1", day=1 + i % 25,
                                       liiga="Meistriliiga", sport="vorkpall", level=1))
        fut = Event(**{**ev(2999, "A", "D", "", liiga="Meistriliiga", sport="vorkpall").__dict__, "start": datetime(2026, 6, 20, 18, tzinfo=TALLINN)})   # sama hooaeg (võrkpall: juuli–juuni)
        u = self.build(base + [fut]).for_game(fut)
        self.assertTrue(u["ennustus"])
        txt = " ".join(i for s in u["enne"] for i in s["items"])
        self.assertIn("ei ole testitud", txt)                                         # täpsustav lause
        self.assertIn("kihlveo nõuanne", txt)
        self.assertNotIn("viik", txt.lower().replace("viigiga", ""))                  # võrkpallis viiki pole
        pr = self.build(base + [fut]).recs["e2999"].pr
        self.assertEqual(pr[1], 0.0)
        self.assertAlmostEqual(pr[0] + pr[2], 1.0)
        self.assertGreater(pr[0], 0.5)                                                 # A on tugevaim
        done = self.build(base + [fut]).for_game(base[-1])                            # mängitud võrkpallimäng: täpsustus ka pärast mängu
        self.assertIn("ei ole testitud", " ".join(i for s in done["parast"] for i in s["items"]))

    def test_teised_alad_saavad_faktid(self):
        k = [ev(3000 + i, a, b, "80-70", day=1 + i, sport="korvpall", liiga="KML") for i, (a, b) in enumerate([("A", "B"), ("B", "C"), ("A", "C")])]
        fut = Event(**{**ev(3999, "A", "B", "", sport="korvpall", liiga="KML").__dict__, "start": datetime(2026, 7, 1, 18, tzinfo=TALLINN)})
        u = self.build(k + [fut]).for_game(fut)
        self.assertFalse(u["ennustus"])
        txt = " ".join(i for s in u["enne"] for i in s["items"])
        self.assertIn("punkti", txt)                                                  # korvpallis punktid, mitte väravad
        self.assertTrue(any("Omavahelised" in s["title"] for s in u["enne"]))


if __name__ == "__main__":
    unittest.main()
