import unittest
from datetime import date
from types import SimpleNamespace

from analuus import ennustus as en
from analuus import tulemus as tul


def mang(i, kodu, kyl, a, b, hoo="2026"):
    return SimpleNamespace(id=str(i), sport="jalgpall", liiga="L", hooaeg=hoo, paev=date(2026, 3, 1 + i % 28), kodu=kodu, kylaline=kyl,
                           t=tul.Tulemus(a, b), jarjekord=(i,))


class EloTest(unittest.TestCase):
    def test_tõenäosused_on_jaotus_ja_vordsed_annavad_kodueelise(self):
        p = en.Parameetrid()
        ph, pd, pa = en.tõenäosused(1500, 1500, p)
        self.assertAlmostEqual(ph + pd + pa, 1.0)
        self.assertGreater(ph, pa)
        ph2, _, pa2 = en.tõenäosused(1700, 1500, p)
        self.assertGreater(ph2, ph)
        self.assertLess(pa2, pa)

    def test_ennustus_ei_kasuta_oma_tulemust(self):
        a = [mang(1, "A", "B", 2, 0), mang(2, "B", "C", 1, 1), mang(3, "A", "C", 3, 0)]
        b = [a[0], a[1], mang(3, "A", "C", 0, 5)]
        pa = [pr for _, pr, *_ in en.kaiguta(a, en.Parameetrid())]
        pb = [pr for _, pr, *_ in en.kaiguta(b, en.Parameetrid())]
        self.assertEqual(pa, pb)   # viimase mängu tulemus ei muuda selle ennustust

    def test_voit_tostab_reitingut_ja_mangude_arv_enne(self):
        g = [mang(1, "A", "B", 1, 0), mang(2, "A", "B", 1, 0)]
        rows = list(en.kaiguta(g, en.Parameetrid()))
        self.assertGreater(rows[1][1][0], rows[0][1][0])
        self.assertEqual((rows[0][3], rows[1][3]), (0, 1))

    def test_taandumine_tombab_keskmise_poole(self):
        r = {"A": 1600.0, "B": 1400.0}
        en.taanda(r, 0.5)
        self.assertEqual((r["A"], r["B"]), (1550.0, 1450.0))

    def test_hooaja_vahetusel_taandub(self):
        g = [mang(1, "A", "B", 3, 0, "2025"), mang(2, "A", "B", 3, 0, "2026")]
        full = list(en.kaiguta(g, en.Parameetrid(taandumine=0.0)))[1][1][0]
        half = list(en.kaiguta(g, en.Parameetrid(taandumine=0.5)))[1][1][0]
        self.assertGreater(full, half)


class KaheTulemusegaTest(unittest.TestCase):
    def test_summa_on_yks_viiki_pole_ja_kodueelis_toimib(self):
        p = en.Parameetrid(kodueelis=60.0)
        ph, pv, pg = en.tõenäosused_kaks(1500, 1500, p)
        self.assertEqual(pv, 0.0)
        self.assertAlmostEqual(ph + pg, 1.0)
        self.assertGreater(ph, 0.5)
        self.assertGreater(en.tõenäosused_kaks(1700, 1500, p)[0], ph)


class MoodikudTest(unittest.TestCase):
    def test_brier(self):
        self.assertEqual(en.brier((1, 0, 0), "kodu"), 0.0)
        self.assertEqual(en.brier((0, 0, 1), "kodu"), 2.0)
        self.assertAlmostEqual(en.brier((1 / 3,) * 3, "viik"), 2 / 3)

    def test_tapsus_ja_kalibratsioon(self):
        rows = [((0.7, 0.1, 0.2), "kodu"), ((0.7, 0.1, 0.2), "kylaline"), ((0.2, 0.1, 0.7), "kylaline")]
        self.assertAlmostEqual(en.hinda(rows)["tapsus"], 2 / 3)
        kal = en.kalibratsioon(rows, bins=10)
        self.assertEqual([k["n"] for k in kal], [1, 2])
        self.assertAlmostEqual(kal[1]["tegelik"], 0.5)

    def test_tabeli_valik_kasutab_ainult_varasemaid(self):
        g = [mang(1, "A", "B", 2, 0), mang(2, "B", "A", 0, 1)]
        rows = list(en.tabeli_ennustus(g))
        self.assertEqual(rows[0][1], "kodu")      # alguses viik → kodu
        self.assertEqual(rows[1][1], "kylaline")  # A on tabelis ees, B koduväljakul


if __name__ == "__main__":
    unittest.main()
