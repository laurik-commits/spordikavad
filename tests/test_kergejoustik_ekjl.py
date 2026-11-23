import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config, kergejoustik_ekjl as adapter
from scrapers.geo import Geo
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "kergejoustik_ekjl.html"


class KergejoustikEkjlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def find(self, title):
        return next(e for e in self.events if e.home == title)

    def test_count_and_skipped(self):
        # 142 kaarti: välja jäävad koolitus, koosolekud, auhinnagala ja tiitlivõistlused (GL/GW/OW)
        self.assertEqual(len(self.events), 132)
        titles = {e.home for e in self.events}
        self.assertNotIn("Kergejõustikukohtunike aastakoosolek 2026", titles)
        self.assertNotIn("Eesti Kergejõustikuauhinnad 2026", titles)
        self.assertNotIn("XXXIV Olümpiamängud", titles)

    def test_event_row(self):
        e = self.find("Eesti talvised meistrivõistlused 2027")
        self.assertEqual(e.sport, "kergejoustik")
        self.assertEqual((e.away, e.venue, e.level), ("", "Lasnamäe Kergejõustikuhall", 1))
        self.assertEqual(e.start.date(), date(2027, 2, 20))
        self.assertEqual(e.end, "2027-02-21")   # kahepäevane
        self.assertTrue(e.time_tbc)
        self.assertEqual(e.league, "Täiskasvanute võistlused")

    def test_time_and_youth(self):
        e = self.find("Ida-Virumaa TV 10 OLÜMPIASTARTI I etapp")
        self.assertEqual(e.start, datetime(2026, 11, 25, 11, 0, tzinfo=TALLINN))
        self.assertFalse(e.time_tbc)
        self.assertEqual((e.level, e.league), (4, "Noorte võistlused"))
        self.assertEqual(self.find("Eesti talvised meistrivõistlused(U18, U20, U23) 2027").level, 4)

    def test_levels(self):
        self.assertEqual(self.find("Swedbanki Tallinna Maraton – 42,195 km").level, 1)   # kategooria E
        self.assertEqual(self.find("Eesti murdmaajooksu meistrivõistlused 2027").level, 1)
        self.assertEqual(self.find("Nõmme KJK jõuluvõistlus").level, 3)                  # kohalik, peidetud

    def test_all_estonian_venues_known_and_foreign_dropped(self):
        cfg = config.load()
        venues = Venues.load()
        kept = build.only_estonia(self.events, venues, Geo(cfg))
        self.assertEqual(venues.unknown, set())
        self.assertNotIn("Valencia", {e.venue for e in kept})
        self.assertIn("Tallinn", {e.city for e in kept})


if __name__ == "__main__":
    unittest.main()
