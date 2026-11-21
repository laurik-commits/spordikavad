import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config, korvpall_ut as adapter
from scrapers.geo import Geo
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "korvpall_ut.html"


class KorvpallUtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def find(self, d, away):
        return next(e for e in self.events if e.start.date() == d and e.away == away)

    def test_only_home_games(self):
        # 39 kuupäevaga rida, neist 20 Tartu kodumängu (võõrsil mängude KOHT on ainult linn)
        self.assertEqual(len(self.events), 20)
        self.assertEqual({e.home for e in self.events}, {"Tartu Ülikool Maks&Moorits"})
        self.assertEqual({e.venue for e in self.events}, {"TÜ sph"})

    def test_home_game(self):
        e = self.find(date(2026, 10, 24), "TalTech/ALEXELA")
        self.assertEqual(e.start, datetime(2026, 10, 24, 19, 0, tzinfo=TALLINN))
        self.assertEqual(e.league, "Eesti-Läti Korvpalliliiga")
        self.assertEqual(e.sport, "korvpall")
        self.assertFalse(e.time_tbc)

    def test_results_in_last_column(self):
        self.assertEqual(self.find(date(2026, 10, 24), "TalTech/ALEXELA").result, "65-41")
        played = [e for e in self.events if e.result]
        self.assertEqual(len(played), 6)
        self.assertTrue(all(e.start.date() < date(2026, 11, 21) for e in played))  # mängimata mängul tulemust pole

    def test_time_formats(self):
        self.assertEqual(self.find(date(2026, 10, 6), "Dziki Warsaw").start.hour, 19)       # "19.00"
        self.assertEqual(self.find(date(2026, 9, 24), "Bigbank/Kalev").start.hour, 19)      # "19:00"
        self.assertEqual(self.find(date(2026, 11, 7), "Valmiera").start.hour, 18)

    def test_leagues(self):
        self.assertEqual({e.league for e in self.events},
                         {"Eesti-Läti Korvpalliliiga", "FIBA Europe Cup", "Eelhooaja mäng"})
        self.assertEqual(self.find(date(2026, 11, 18), "Skopje").league, "FIBA Europe Cup")

    def test_ranges_are_skipped(self):
        # eelhooaja turniirid (04.-05.09) ja karikavõistlus (15.-20.02) pole üksikmängud
        self.assertFalse(any(e.league == "PRESEASON TOURNAMENT" or e.start.date() == date(2027, 2, 20)
                             for e in self.events))

    def test_geo_filter_keeps_all_home_games_in_tartu(self):
        entry = {}
        kept = build.only_estonia(self.events, Venues.load(), Geo(config.load()), date(2026, 11, 20), entry)
        self.assertEqual(len(kept), 20)
        self.assertEqual({(e.venue, e.city) for e in kept}, {("Tartu Ülikooli spordihoone", "Tartu")})
        self.assertNotIn("no_venue", entry)

    def test_unique_ids(self):
        self.assertEqual(len({e.id for e in self.events}), len(self.events))


if __name__ == "__main__":
    unittest.main()
