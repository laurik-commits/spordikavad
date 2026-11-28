"""Spordikaart: andmete koostamine ja leht /kaart/; /analuus/ „tulekul“ leht."""
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


class KoostaTest(unittest.TestCase):
    def test_structure(self):
        evs = [ev(0, "Hall A", "2-0"), ev(60, "Hall A väike", "", sport="korvpall"), ev(61, "Hall B", "", tbc=True, away=""),
               ev(2, "Hall A", "1-0", level=3), ev(3, "Tundmatu", "1-0")]
        d, tekstid = kaart.koosta(evs, paigad(), TODAY, cities=[{"slug": "tallinn", "name": "Tallinn"}, {"slug": "tartu", "name": "Tartu"}])
        self.assertEqual([k["n"] for k in d["kohad"]], ["Hall A", "Hall B"])
        self.assertEqual(len(tekstid), len(d["mangud"]))                       # tekstid samas järjekorras
        self.assertEqual([c["s"] for c in d["linnad"]], ["tallinn", "tartu"])
        self.assertEqual(d["mangud"][0][5], evs[0].id)                         # rea lõpus mängu id
        self.assertEqual(len(d["mangud"]), 3)                                  # peidetud tase (3) ja tundmatu koht välja
        self.assertEqual([a["k"] for a in d["alad"]], ["jalgpall", "korvpall"])
        a = d["mangud"][0]
        self.assertEqual((a[0], a[1], a[2], a[3], a[4]), (0, (date(2026, 10, 1) - kaart.ALGUS).days, 18 * 60, 0, 1))
        tbc = next(m for m in d["mangud"] if m[0] == 1)
        self.assertEqual(tbc[2], -1)                                           # kellaaeg teadmata
        self.assertEqual(tekstid[2][0], "H")                                   # üritus: ainult nimi
        self.assertTrue(d["kohad"][1]["t"] == "umbes")
        json.dumps(d)

    def test_places_without_events_are_not_listed(self):
        d, _ = kaart.koosta([ev(0, "Hall A", "2-0")], paigad(), TODAY)
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
        self.assertNotIn("Halli mõju", page)                       # statistika on lehel /analuus/, mitte kaardil
        self.assertNotIn("<table", page)
        self.assertIn('<script src="../vendor/leaflet/leaflet.js" defer>', page)
        data = json.loads(self.read("kaart/andmed.json"))
        self.assertEqual([k["n"] for k in data["kohad"]], ["Kalevi keskstaadioni kunstmuruväljak"])   # paigad.toml nimi
        self.assertTrue((self.out / "vendor" / "leaflet" / "leaflet.js").exists())
        self.assertTrue((self.out / "vendor" / "leaflet" / "LICENSE").exists())
        self.assertTrue((self.out / "kaart" / "kaart.js").exists())

    def test_in_sitemap_menu_and_links_resolve(self):
        self.assertIn("<loc>https://example.org/kaart/</loc>", self.read("sitemap.xml"))
        self.assertIn('href="kaart/?linn=tallinn"', self.read("index.html"))   # menüülink: linnalehelt avaneb kaart selle linna vaates
        page = self.out / "kaart" / "index.html"
        for href in re.findall(r'(?:href|src)="([^"#?]+)"', page.read_text(encoding="utf-8")):
            if href.startswith(("http", "mailto:")):
                continue
            self.assertTrue((page.parent / href).exists(), href)

    def test_analuus_page_is_coming_soon_and_not_indexed(self):
        page = self.read("analuus/index.html")
        self.assertIn("Tulekul", page)
        self.assertIn('content="noindex"', page)
        self.assertNotIn("<table", page)                          # halli mõju tabelit ei avaldata enne ülevaatust
        self.assertNotIn("/analuus/", self.read("sitemap.xml"))
        self.assertIn('href="analuus/"', self.read("index.html"))   # menüülink

    def test_texts_file_matches_rows_and_state_in_url_script(self):
        data = json.loads(self.read("kaart/andmed.json"))
        tekstid = json.loads(self.read("kaart/tekstid.json"))
        self.assertEqual(len(tekstid), len(data["mangud"]))
        js = self.read("kaart/kaart.js")
        for key in ("pushState", "replaceState", "popstate", "URLSearchParams", "Kogu Eesti" if False else "EESTI"):
            self.assertIn(key, js)
        page = self.read("kaart/index.html")
        self.assertIn("Nädal (7 päeva)", page)                   # päris nädalavaade, mitte „tüüpiline nädal“
        for gone in ("nadalapaev", "kellarida", "Tüüpiline nädal", 'id="kell"'):
            self.assertNotIn(gone, page)
        self.assertNotIn("AKEN", js)
        self.assertIn("paevakiri", js)                           # nädalavaates päevapealkirjad
        self.assertIn('id="filtritoggle"', page)
        self.assertIn('id="kogu"', page)
        self.assertLess(page.index('id="map"'), page.index('id="kontrollid"'))   # kaart on dokumendis esimene (mobiilis kohe päise all)

    def test_reserved_folder_names(self):
        from scrapers.model import SPORTS
        self.assertFalse({"kaart", "vendor", "analuus"} & set(SPORTS))


if __name__ == "__main__":
    unittest.main()
