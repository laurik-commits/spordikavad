"""Spordikaart: andmete koostamine, halli mõju (kodu võidud ootuse suhtes) ja leht /kaart/."""
import json
import re
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import build
from analuus import kaart
from analuus.paigad import Paigad
from scrapers import config
from scrapers.model import TALLINN, new_event

TODAY = date(2026, 11, 20)
TOML = '''
[[paik]]
nimi = "Hall A"
linn = "Tallinn"
lat = 59.43
lon = 24.75
tapsus = "tapne"
kohad = ["Hall A", "Hall A väike"]

[[paik]]
nimi = "Hall B"
linn = "Tartu"
lat = 58.38
lon = 26.72
tapsus = "umbes"
kohad = ["Hall B"]
'''
VENUES = '''
[[venue]]
name = "Hall A"
city = "Tallinn"
[[venue]]
name = "Hall A väike"
city = "Tallinn"
[[venue]]
name = "Hall B"
city = "Tartu"
'''


def paigad():
    d = Path(tempfile.mkdtemp())
    (d / "p.toml").write_text(TOML, encoding="utf-8")
    (d / "v.toml").write_text(VENUES, encoding="utf-8")
    return Paigad.load(d / "p.toml", d / "v.toml")


def ev(day, venue, result="", home="H", away="V", sport="jalgpall", league="Liiga", level=1, hour=18, tbc=False):
    d = date(2026, 10, 1) + timedelta(days=day)
    return new_event(source="t", sport=sport, league=league, start=datetime(d.year, d.month, d.day, hour, 0, tzinfo=TALLINN), home=home,
                     away=away, venue=venue, city="Tallinn", url="https://example.org/", result=result, level=level, time_tbc=tbc)


class WilsonTest(unittest.TestCase):
    def test_interval(self):
        lo, hi = kaart.wilson(50, 100)
        self.assertAlmostEqual(lo, 40.4, delta=0.2)
        self.assertAlmostEqual(hi, 59.6, delta=0.2)
        self.assertEqual(kaart.wilson(0, 0), (0.0, 0.0))
        lo, hi = kaart.wilson(15, 15)
        self.assertGreater(lo, 78)     # 15/15: alumine piir pole 100, väike valim
        self.assertLess(lo, 100)


class HalliMojuTest(unittest.TestCase):
    def test_threshold_expected_and_flags(self):
        # Hall A: 30 mängu, kodu võidab 28 (93,3%); Hall B: 30 mängu, kodu võidab 12 (40%); liigas kokku 40/60 = 66,7% → ootus 66,7%
        evs = ([ev(i, "Hall A", "2-0" if i < 28 else "0-1", home=f"A{i % 3}") for i in range(30)] +
               [ev(i, "Hall B", "1-0" if i < 12 else "0-2", home=f"B{i % 2}") for i in range(30)])
        r = {x["paik"]: x for x in kaart.halli_moju(evs, paigad())}
        a, b = r["Hall A"], r["Hall B"]
        self.assertEqual((a["n"], a["kodu"], a["kodu_pct"], a["oodatav_pct"], a["vahe_pp"]), (30, 28, 93.3, 66.7, 26.7))
        self.assertEqual(a["kodumeeskondi"], 3)
        self.assertTrue(a["oluline"])                      # 66,7% on 93,3% vahemikust väljas
        self.assertTrue(b["oluline"])
        self.assertEqual((b["kodu_pct"], b["vahe_pp"]), (40.0, -26.7))
        self.assertLess(a["lo"], a["kodu_pct"])
        self.assertGreater(a["hi"], a["kodu_pct"])

    def test_small_samples_draws_and_unknown_venues_are_left_out(self):
        evs = [ev(i, "Hall A", "1-1") for i in range(14)]                       # 14 < 15
        self.assertEqual(kaart.halli_moju(evs, paigad()), [])
        evs += [ev(20, "Hall A", "1-1")]
        r = kaart.halli_moju(evs, paigad())[0]
        self.assertEqual((r["n"], r["kodu"], r["viik"], r["viik_pct"]), (15, 0, 15, 100.0))
        self.assertEqual(kaart.halli_moju([ev(i, "Tundmatu", "1-0") for i in range(30)], paigad()), [])
        self.assertEqual(kaart.halli_moju([ev(i, "Hall A", "") for i in range(30)], paigad()), [])    # tulemusteta mänge ei arvestata

    def test_merged_places_count_together(self):
        evs = [ev(i, "Hall A" if i % 2 else "Hall A väike", "1-0") for i in range(16)]
        self.assertEqual(kaart.halli_moju(evs, paigad())[0]["n"], 16)        # kaks venues.toml kohta, üks paik


class KoostaTest(unittest.TestCase):
    def test_structure(self):
        evs = [ev(0, "Hall A", "2-0"), ev(60, "Hall A väike", "", sport="korvpall"), ev(61, "Hall B", "", tbc=True, away=""),
               ev(2, "Hall A", "1-0", level=3), ev(3, "Tundmatu", "1-0")]
        d = kaart.koosta(evs, paigad(), TODAY)
        self.assertEqual([k["n"] for k in d["kohad"]], ["Hall A", "Hall B"])
        self.assertEqual(len(d["mangud"]), 3)                                  # peidetud tase (3) ja tundmatu koht välja
        self.assertEqual([a["k"] for a in d["alad"]], ["jalgpall", "korvpall"])
        a = d["mangud"][0]
        self.assertEqual((a[0], a[1], a[2], a[3], a[4]), (0, (date(2026, 10, 1) - kaart.ALGUS).days, 18 * 60, 0, 1))
        tbc = next(m for m in d["mangud"] if m[0] == 1)
        self.assertEqual(tbc[2], -1)                                           # kellaaeg teadmata
        self.assertEqual(len(d["tulevased"]), 2)                               # ainult 20.11 ja hilisemad (päevad 60 ja 61)
        self.assertEqual(d["tulevased"][1]["t"], "H")                          # üritus: ainult nimi
        self.assertTrue(d["kohad"][1]["t"] == "umbes")
        json.dumps(d)

    def test_places_without_events_are_not_listed(self):
        d = kaart.koosta([ev(0, "Hall A", "2-0")], paigad(), TODAY)
        self.assertEqual([k["n"] for k in d["kohad"]], ["Hall A"])


class KaartLehtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp())
        evs = [ev(i, "Kalevi spordihall", "2-1", home=f"H{i % 4}", away="V", league="Liiga") for i in range(20)] + [ev(50, "Kalevi spordihall", "")]
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/", "default_level": 1},
               "geo": dict(config.load()["geo"], default="tallinn"), "source": config.load()["source"]}
        build.render(evs, cfg, date(2026, 10, 25), cls.out)

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_page_data_and_assets(self):
        page = self.read("kaart/index.html")
        self.assertIn("Andmed katavad ainult kalendris olevaid liigasid", page)
        self.assertIn("OpenStreetMapi", page)                     # aluskaardi viide
        self.assertIn("See ei ole põhjuslik", page)
        self.assertIn('<script src="../vendor/leaflet/leaflet.js" defer>', page)
        data = json.loads(self.read("kaart/andmed.json"))
        self.assertEqual([k["n"] for k in data["kohad"]], ["Kalevi keskstaadioni kunstmuruväljak"])   # paigad.toml nimi
        self.assertTrue((self.out / "vendor" / "leaflet" / "leaflet.js").exists())
        self.assertTrue((self.out / "vendor" / "leaflet" / "LICENSE").exists())
        self.assertTrue((self.out / "kaart" / "kaart.js").exists())

    def test_in_sitemap_menu_and_links_resolve(self):
        self.assertIn("<loc>https://example.org/kaart/</loc>", self.read("sitemap.xml"))
        self.assertIn('href="kaart/"', self.read("index.html"))   # menüülink
        page = self.out / "kaart" / "index.html"
        for href in re.findall(r'(?:href|src)="([^"#?]+)"', page.read_text(encoding="utf-8")):
            if href.startswith(("http", "mailto:")):
                continue
            self.assertTrue((page.parent / href).exists(), href)

    def test_home_win_table_rendered(self):
        page = self.read("kaart/index.html")
        self.assertIn("Kalevi keskstaadioni kunstmuruväljak, Tallinn", page)
        self.assertRegex(page, r"<td>20</td><td>\d+,\d%</td>")   # komaga arvud

    def test_reserved_folder_names(self):
        from scrapers.model import SPORTS
        self.assertFalse({"kaart", "vendor"} & set(SPORTS))


if __name__ == "__main__":
    unittest.main()
