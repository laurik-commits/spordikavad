import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, ujumine_eul as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "ujumine_eul.html"


class UjumineEulTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def find(self, title):
        return next(e for e in self.events if e.home == title)

    def test_skips_trainings_and_merges_duplicates(self):
        titles = [e.home for e in self.events]
        self.assertFalse([t for t in titles if "koolitus" in t.lower() or "veeohutus" in t.lower()])
        self.assertEqual(titles.count("Yess talvestardid"), 1)
        self.assertEqual(self.find("Yess talvestardid").venue, "Tartu, Aura Veekeskus")  # pikem koha kirjapilt jääb

    def test_event_row(self):
        e = self.find("Eesti lühiraja meistrivõistlused 2026")
        self.assertEqual((e.sport, e.level, e.away, e.venue), ("ujumine", 1, "", "Kohtla-Järve"))
        self.assertEqual(e.start.date(), date(2026, 12, 18))
        self.assertEqual(e.end, "2026-12-20")
        self.assertTrue(e.time_tbc)

    def test_levels(self):
        self.assertEqual(self.find("Eesti masters-ujumise lühiraja meistrivõistlused (Supermasters)").level, 1)
        self.assertEqual(self.find("Wiru Swim Cup").level, 2)
        self.assertEqual(self.find("Speedo Räimeralli FINAAL").level, 4)
        self.assertEqual(self.find("Tartumaa MV").level, 3)
        self.assertEqual(self.find("Audentese Jõuluvõistlus").level, 3)

    def test_venues_known_and_foreign_dropped(self):
        cfg = config.load()
        venues = Venues.load()
        kept = build.only_estonia(self.events, venues, Geo(cfg))
        self.assertEqual(venues.unknown, set())
        venue_names = {e.venue for e in kept}
        self.assertNotIn("Peking", venue_names)
        self.assertNotIn("Leedu", venue_names)
        self.assertIn("Tartu", {e.city for e in kept})
        self.assertIn("Aura Veekeskus", venue_names)


if __name__ == "__main__":
    unittest.main()
