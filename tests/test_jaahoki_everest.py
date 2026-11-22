import unittest
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config, jaahoki_everest as adapter, jaahoki_vipers
from scrapers.geo import Geo
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURES = Path(__file__).parent / "fixtures"


class JaahokiEverestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse((FIXTURES / "jaahoki_everest.html").read_text(encoding="utf-8"))
        cls.venues, cls.geo = Venues.load(), Geo(config.load())

    def test_leagues_and_levels(self):
        # 91 kaarti; U12, U10 ja U8 ning kuupäevata ("TBD") kaardid jäävad välja
        self.assertEqual(Counter((e.league, e.level) for e in self.events), {
            ("Unibet Hokiliiga", 1): 10, ("Naiste hokiliiga", 1): 8,
            ("U19 noorteliiga", 4): 13, ("U16 noorteliiga", 4): 15})
        self.assertTrue(all("HC Everest" in (e.home, e.away) for e in self.events))

    def test_away_game_has_real_venue(self):
        e = next(e for e in self.events if e.start.date() == date(2026, 12, 6))
        self.assertEqual((e.home, e.away, e.venue), ("Narva PSK", "HC Everest", "Narva jäähall"))
        self.assertEqual(e.start, datetime(2026, 12, 6, 16, 30, tzinfo=TALLINN))
        self.assertEqual(e.url, adapter.URL)
        self.assertFalse(e.time_tbc)
        # Vipersi lehel on see mäng kirjas Tondirabas, Everesti lehel õigesti Kohtla-Järvel
        e = next(e for e in self.events if e.start.date() == date(2027, 1, 16) and e.league == "Unibet Hokiliiga")
        self.assertEqual((e.home, e.away, e.venue), ("HC Everest", "HC Vipers", "Kohtla-Järve jäähall"))

    def test_geo_filter_keeps_all_games(self):
        entry = {}
        kept = build.only_estonia(self.events, self.venues, self.geo, date(2026, 11, 22), entry)
        self.assertEqual(len(kept), len(self.events))
        self.assertEqual({(e.venue, e.city) for e in kept}, {
            ("Kohtla-Järve jäähall", "Kohtla-Järve"), ("Narva jäähall", "Narva"), ("Astri Arena", "Tartu"),
            ("Tondiraba jäähall", "Tallinn"), ("Haabersti jäähall", "Tallinn")})
        self.assertNotIn("no_venue", entry)

    def test_vipers_home_games_come_from_vipers(self):
        vipers = jaahoki_vipers.parse((FIXTURES / "jaahoki_vipers.html").read_text(encoding="utf-8"))
        kept, removed = build.dedupe(build.only_estonia(vipers + self.events, self.venues, self.geo))
        self.assertEqual(removed, 2)   # 28.11 ja 30.01 HC Vipers – HC Everest Tondirabas
        both = [e for e in kept if {e.home, e.away} == {"HC Vipers", "HC Everest"} and e.league == "Unibet Hokiliiga"]
        self.assertEqual(sorted((e.start.date(), e.source) for e in both), [
            (date(2026, 11, 28), "jaahoki_vipers"), (date(2027, 1, 16), "jaahoki_everest"),
            (date(2027, 1, 30), "jaahoki_vipers")])

    def test_commented_out_and_undated_cards_are_skipped(self):
        card = ('<a href="https://ehs.eestihoki.ee/" class="card-header">UNIBET HOKILIIGA</a><div class="card-body">'
                '<h5 class="card-title">{when}</h5><h6 class="card-subtitle mb-2 text-muted">Narva jäähall</h6>'
                '<p class="card-text">Narva PSK - HC Everest</p>')
        self.assertEqual(adapter.parse("<!-- " + card.format(when="01.03.2027 16:00") + " -->"), [])
        self.assertEqual(adapter.parse(card.format(when="TBD 16:00")), [])
        e, = adapter.parse(card.format(when="01.03.2027"))
        self.assertTrue(e.time_tbc)

    def test_source_order(self):
        names = [s["name"] for s in config.load()["source"]]
        self.assertLess(names.index("jaahoki_vipers"), names.index(adapter.NAME))
        self.assertLess(names.index(adapter.NAME), names.index("kasitsi"))

    def test_unique_ids(self):
        # 04.04.2027 on U16-l kaks mängu HC Everest – HC Vipers (12:30 ja 14:30): ID-d peavad erinema
        self.assertEqual(len({e.id for e in self.events}), len(self.events))
        double = [e for e in self.events if e.start.date() == date(2027, 4, 4) and e.away == "HC Vipers"]
        self.assertEqual(len(double), 2)


if __name__ == "__main__":
    unittest.main()
