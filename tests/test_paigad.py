"""Toimumiskohtade tabel (paigad.toml): kohad on venues.toml-is, duplikaadid seotud ühe paigaga, koordinaadid Eestis."""
import tempfile
import tomllib
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from analuus import geokodeeri
from analuus.paigad import Paigad, PATH
from scrapers.model import TALLINN, new_event

TOML = '''
[[paik]]
nimi = "Maarjamäe"
linn = "Tallinn"
lat = 59.43
lon = 24.83
tapsus = "tapne"
kohad = ["Maarjamäe staadion", "Maarjamäe kunstmuruväljak"]

[[paik]]
nimi = "Tartu"
linn = "Tartu"
lat = 58.378
lon = 26.729
tapsus = "linn"
kohad = ["Tartu"]
'''
VENUES = '''
[[venue]]
name = "Maarjamäe staadion"
city = "Tallinn"
aliases = ["Maarjamäe Stadium"]

[[venue]]
name = "Maarjamäe kunstmuruväljak"
city = "Tallinn"

[[venue]]
name = "Tartu"
city = "Tartu"
'''


def files(toml=TOML, venues=VENUES):
    d = Path(tempfile.mkdtemp())
    (d / "paigad.toml").write_text(toml, encoding="utf-8")
    (d / "venues.toml").write_text(venues, encoding="utf-8")
    return d / "paigad.toml", d / "venues.toml"


def ev(venue, city="Tallinn", sport="jalgpall"):
    return new_event(source="t", sport=sport, league="L", start=datetime(2026, 10, 1, 18, 0, tzinfo=TALLINN), home="A", away="B",
                     venue=venue, city=city, url="https://example.org/")


class PaigadTest(unittest.TestCase):
    def test_duplicates_share_one_place_and_aliases_collected(self):
        pg = Paigad.load(*files())
        a, b = pg.paik_of("Maarjamäe staadion"), pg.paik_of("Maarjamäe kunstmuruväljak")
        self.assertIs(a, b)
        self.assertEqual(a.aliased, ("Maarjamäe Stadium",))
        self.assertIsNone(pg.paik_of("Tundmatu"))

    def test_table_and_missing(self):
        pg = Paigad.load(*files())
        evs = [ev("Maarjamäe staadion"), ev("Maarjamäe kunstmuruväljak"), ev("Maarjamäe kunstmuruväljak", sport="korvpall"), ev("Uus koht")]
        t = pg.tabel(evs)
        self.assertEqual((t[0]["paik"].nimi, t[0]["mange"], t[0]["alad"]), ("Maarjamäe", 3, {"jalgpall": 2, "korvpall": 1}))
        self.assertEqual(pg.puudu(evs), [("Uus koht", "Tallinn", 1)])

    def test_errors(self):
        with self.assertRaises(ValueError):   # sama koht kahes paigas
            Paigad.load(*files(TOML + '\n[[paik]]\nnimi = "X"\nlinn = "Tallinn"\nlat = 59.4\nlon = 24.7\ntapsus = "tapne"\nkohad = ["Maarjamäe staadion"]\n'))
        with self.assertRaises(ValueError):   # väljaspool Eestit
            Paigad.load(*files(TOML.replace("lat = 59.43", "lat = 48.85")))
        with self.assertRaises(ValueError):   # tundmatu täpsus
            Paigad.load(*files(TOML.replace('tapsus = "tapne"', 'tapsus = "arvatud"')))


@unittest.skipUnless(PATH.exists(), "paigad.toml pole veel koostatud (etapp 2 pooleli)")
class RepoTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pg = Paigad.load()
        root = Path(__file__).parent.parent
        cls.venues = {v["name"]: v["city"] for v in tomllib.loads((root / "venues.toml").read_text(encoding="utf-8"))["venue"]}

    def test_all_places_reference_known_venues_in_same_city(self):
        self.assertGreater(len(self.pg.paigad), 100)
        for p in self.pg.paigad:
            for k in p.kohad:
                self.assertIn(k, self.venues, f"{p.nimi}: koht {k!r} puudub venues.toml-ist")
                self.assertEqual(self.venues[k], p.linn, f"{p.nimi}: {k!r} on venues.toml-is linnas {self.venues[k]!r}, paigas {p.linn!r}")

    def test_no_unmerged_duplicates_within_30_m(self):
        exact = [p for p in self.pg.paigad if p.tapsus == "tapne"]
        close = []
        for i, a in enumerate(exact):
            for b in exact[i + 1:]:
                if a.linn == b.linn and geokodeeri.kaugus_km((a.lat, a.lon), (b.lat, b.lon)) < 0.03:
                    close.append((a.nimi, b.nimi))
        self.assertEqual(close, [], "kaks paika alla 30 m kaugusel: liida need ühe paigana (kohad = [...])")

    def test_real_events_have_places(self):
        from analuus.andmed import load_events
        evs = [e for e in load_events() if e.venue]
        katmata = sum(1 for e in evs if self.pg.paik_of(e.venue) is None)
        self.assertLess(katmata / len(evs), 0.05, f"{katmata}/{len(evs)} mängul pole paika: python -m analuus.paigad --puudu")


class GeokoodTest(unittest.TestCase):
    def test_distance(self):
        self.assertAlmostEqual(geokodeeri.kaugus_km((59.437, 24.754), (58.378, 26.729)), 165.6, delta=3)   # Tallinn–Tartu (linnulennult)

    def _run(self, results, nimi="Raja jalgpallihall", city="Tallinn"):
        def fake(q, limit=4):
            if q == f"{city}, Eesti":
                return [{"lat": "59.437", "lon": "24.754", "category": "boundary"}]
            return results.get(q, [])
        with mock.patch.object(geokodeeri, "paring", fake):
            return geokodeeri.geokodeeri(nimi, city, {})

    def test_exact_candidate_near_city(self):
        r = self._run({"Raja jalgpallihall, Tallinn": [{"lat": "59.43", "lon": "24.71", "category": "leisure", "name": "Raja jalgpallihall",
                                                         "display_name": "Raja", "osm_type": "way", "osm_id": 1}]})
        self.assertEqual((r["tapsus"], r["lat"], r["lon"]), ("tapne", 59.43, 24.71))

    def test_far_candidate_falls_back_to_city_centre(self):
        r = self._run({"Raja jalgpallihall, Tallinn": [{"lat": "58.378", "lon": "26.729", "category": "leisure", "name": "Raja jalgpallihall"}]})   # Tartus: vale
        self.assertEqual((r["tapsus"], r["lat"], r["lon"]), ("linn", 59.437, 24.754))

    def test_city_placeholder_is_city_level(self):
        r = self._run({}, nimi="Tallinn, koht täpsustamisel")
        self.assertEqual(r["tapsus"], "linn")

    def test_core_words_and_variants(self):
        self.assertEqual(geokodeeri.tuum("Tartu Coop staadioni kunstmuruväljak", "Tartu"), ["coop"])
        self.assertEqual(geokodeeri.tuum("Lasnamäe spordikompleksi kunstmurustaadion", "Tallinn"), ["lasnamae"])
        v = geokodeeri.variandid("Raja jalgpallihall", "Tallinn")
        self.assertEqual(v[:2], ["Raja jalgpallihall, Tallinn", "Raja jalgpallihall"])
        self.assertIn("Raja staadion, Tallinn", v)
        self.assertEqual(len(v), len(set(v)))

    def test_rejects_candidate_without_core_word(self):
        # „Härma staadion“ on lähedal, aga pole „Lasnamäe staadion“
        r = self._run({"Lasnamäe staadion, Tallinn": [{"lat": "59.43", "lon": "24.72", "category": "leisure", "name": "Härma staadion"}]},
                      nimi="Lasnamäe staadion")
        self.assertEqual(r["tapsus"], "linn")

    def test_place_or_district_match_is_only_approximate(self):
        # „Laagri, Saue vald“ annab asula, mitte staadioni: pole „tapne“
        r = self._run({"Laagri kunstmurustaadion, Tallinn": [{"lat": "59.43", "lon": "24.72", "category": "place", "type": "village", "name": "Laagri"}]},
                      nimi="Laagri kunstmurustaadion")
        self.assertEqual(r["tapsus"], "umbes")
        r2 = self._run({"Raja jalgpallihall, Tallinn": [{"lat": "59.43", "lon": "24.71", "category": "building", "type": "sports_hall", "name": "Raja"}]})
        self.assertEqual(r2["tapsus"], "tapne")

    def test_prefers_sports_object_over_street(self):
        r = self._run({"Raja jalgpallihall, Tallinn": [{"lat": "59.431", "lon": "24.711", "category": "place", "name": "Raja", "display_name": "p"},
                                                        {"lat": "59.43", "lon": "24.72", "category": "leisure", "name": "Raja jalgpallihall", "display_name": "l"}]})
        self.assertEqual(r["lat"], 59.43)


if __name__ == "__main__":
    unittest.main()
