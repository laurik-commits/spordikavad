import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, uisutamine_eul as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "uisutamine_eul.html"


class UisutamineEulTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"), "https://www.uisuliit.ee/x")

    def find(self, title):
        return next(e for e in self.events if e.home == title)

    def test_count_and_skipped(self):
        # 30 rida: välja jäävad katsevõistlus, kontrollstart ja kuupäevata (TBA) Narva Cup
        self.assertEqual(len(self.events), 27)
        titles = {e.home for e in self.events}
        self.assertNotIn("Narva Cup", titles)
        self.assertFalse(any("Kontrollstart" in t or "Katsevõistlused" in t for t in titles))

    def test_event_row(self):
        e = self.find("ISU Challenger seeria võistlus Tallinn Trophy 2026")
        self.assertEqual((e.sport, e.away, e.venue, e.level), ("uisutamine", "", "Tondiraba jäähall", 1))
        self.assertEqual((e.start.date(), e.end), (date(2026, 11, 16), "2026-11-22"))
        self.assertEqual(e.league, "Iluuisutamine")
        self.assertTrue(e.time_tbc)
        self.assertEqual(self.find("Talveunistus Trophy 2026").start.date(), date(2026, 10, 30))   # 30.10-01.11
        self.assertEqual(self.find("Talveunistus Trophy 2026").end, "2026-11-01")
        self.assertIn("Tallink Hotels Cup 2027", {e.home for e in self.events})   # esimene link lahtris

    def test_dates(self):
        self.assertEqual(adapter.parse_dates("28.12-02.01.2027"), (date(2026, 12, 28), date(2027, 1, 2)))
        self.assertEqual(adapter.parse_dates("05.12.2026"), (date(2026, 12, 5), None))
        self.assertIsNone(adapter.parse_dates("TBA"))

    def test_levels(self):
        self.assertEqual(self.find("Eesti Meistrivõistlused 2027").level, 1)
        self.assertEqual(self.find("Lõunakeskus Trophy 2026").level, 1)            # ISU kalenderplaan
        self.assertEqual(self.find("Eesti noorte Meistrivõistlused 2027").level, 4)
        self.assertEqual(self.find("Tallinn Trophy Kids 2027").level, 4)
        self.assertEqual(self.find("Crystal Skate Open 2026").level, 3)            # Interclub, peidetud

    def test_season_url(self):
        page = '<a href="/iluuisutamine/voistlused/eul-kalenderplaan-2025-2026">x</a>' \
               '<a href="/iluuisutamine/voistlused/eul-kalenderplaan-2026-2027">y</a>'
        self.assertEqual(adapter.season_url(page),
                         "https://www.uisuliit.ee/iluuisutamine/voistlused/eul-kalenderplaan-2026-2027")
        self.assertEqual(adapter.season_url("<html></html>"), "")

    def test_all_venues_known(self):
        venues = Venues.load()
        kept = build.only_estonia(self.events, venues, Geo(config.load()))
        self.assertEqual(venues.unknown, set())
        self.assertEqual(len(kept), len(self.events))


if __name__ == "__main__":
    unittest.main()
