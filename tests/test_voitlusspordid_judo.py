import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, voitlusspordid_judo as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "voitlusspordid_judo.html"


class VoitlussporidJudoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"), date(2026, 11, 23))

    def test_camp_skipped(self):
        # külgribal 3 üritust: koondiste laager jääb välja
        self.assertEqual([e.home for e in self.events], ["Zen Jõuluturniir", "Klubide Karikavõistlused"])

    def test_event_row(self):
        e = self.events[0]
        self.assertEqual((e.sport, e.league, e.away, e.venue), ("voitlusspordid", "Judo", "", "A. Le Coq Spordihoone"))
        self.assertEqual(e.start.date(), date(2026, 12, 5))
        self.assertEqual(e.url, "https://judo.ee/event/zen-jouluturniir-6/")
        self.assertTrue(e.time_tbc)

    def test_year_rollover(self):
        page = FIXTURE.read_text(encoding="utf-8").replace("05 Dec", "14 Feb")
        self.assertEqual(adapter.parse(page, date(2026, 11, 23))[0].start.date(), date(2027, 2, 14))

    def test_levels(self):
        self.assertEqual(adapter.level_of("European Open Tallinn"), 1)
        self.assertEqual(adapter.level_of("Eesti meistrivõistlused"), 1)
        self.assertEqual(adapter.level_of("Eesti meistrivõistlused U16 ja U21"), 4)
        self.assertEqual(adapter.level_of("Zen Jõuluturniir"), 3)

    def test_venues_known(self):
        venues = Venues.load()
        build.only_estonia(self.events, venues, Geo(config.load()))
        self.assertEqual(venues.unknown, set())


if __name__ == "__main__":
    unittest.main()
