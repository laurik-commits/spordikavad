import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, suusatamine_esl as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "suusatamine_esl.html"
TODAY = date(2026, 11, 23)


class SuusatamineEslTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"), TODAY)

    def find(self, title, venue=None):
        return next(e for e in self.events if e.home == title and (venue is None or e.venue == venue))

    def test_foreign_and_other_dropped(self):
        # 46 rida: välja jäävad Norra, Itaalia ja Soome võistlused (ka "Tromsö, Norra, Eesti"), laagrid ja "Muu"
        self.assertEqual(len(self.events), 32)
        venues = {e.venue for e in self.events}
        for foreign in ("Trysil", "Pozza di Fassa", "Suomu", "Tromsö"):
            self.assertFalse(any(foreign in v for v in venues), foreign)
        titles = {e.home for e in self.events}
        self.assertNotIn("100 suusatundi", titles)
        self.assertNotIn("Talvelaager", titles)

    def test_event_row_and_year(self):
        e = self.find("53. Tartu Maraton")
        self.assertEqual((e.sport, e.away, e.level), ("suusatamine", "", 1))
        self.assertEqual(e.start.date(), date(2027, 2, 27))   # aasta tuletatud: hooaeg üle aastavahetuse
        self.assertEqual(e.end, "2027-02-28")
        self.assertEqual(e.venue, "Otepää-Elva")             # ", Eesti" eemaldatud
        self.assertTrue(e.time_tbc)
        self.assertEqual(e.league, "Murdmaasuusatamine")
        self.assertIn("competition_id=", e.url)
        self.assertEqual(self.find("Vello Liliumi karikavõistlus 2026").start.date(), date(2026, 12, 12))

    def test_levels(self):
        self.assertEqual(self.find("FIS Kahevõistluse MK etapp 2027 Otepääl").level, 1)
        self.assertEqual(self.find("Eesti Meistrivõistlused murdmaasuusatamises", "Mammaste").level, 1)
        self.assertEqual(self.find("Nõo Snacker Noorte MK - Sprint V").level, 4)
        self.assertEqual(self.find("Noorte karikasari, Võru 2026/2027 IV etapp").level, 4)
        self.assertEqual(self.find("29. Tallinna Suusamaraton").level, 1)

    def test_all_venues_known(self):
        venues = Venues.load()
        kept = build.only_estonia(self.events, venues, Geo(config.load()))
        self.assertEqual(venues.unknown, set())
        self.assertEqual(len(kept), len(self.events))
        self.assertIn("Otepää", {e.city for e in kept})


if __name__ == "__main__":
    unittest.main()
