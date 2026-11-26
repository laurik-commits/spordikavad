import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, kurling_ekl as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "kurling_ekl.json"


class KurlingEklTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def find(self, part):
        return next(e for e in self.events if part in e.home)

    def test_only_estonian_events_kept(self):
        # fixtureis 7 sündmust: välismaa (Riia, Östersund, Lohja) ja Eestis toimuvad
        self.assertEqual(len(self.events), 4)
        self.assertTrue(all(e.venue == "Tondiraba Jäähall" for e in self.events))
        titles = " ".join(e.home for e in self.events)
        self.assertNotIn("Riias", titles)
        self.assertNotIn("Naistekoondise", titles)

    def test_multiday_event_row(self):
        e = self.find("Tallinna MK-etapp")
        self.assertEqual((e.sport, e.away, e.level, e.league), ("kurling", "", 1, "Eesti MV ja MK-etapid"))
        self.assertEqual(e.start.date(), date(2027, 1, 18))
        self.assertEqual(e.end, "2027-01-24")
        self.assertTrue(e.time_tbc)                      # terve päeva sündmus
        self.assertEqual(e.url, "https://kurling.ee/kalender/segapaaride-tallinna-mk-etapp/")

    def test_levels_and_single_day(self):
        self.assertEqual(self.find("MM-kvalifikatsioonimängud").level, 2)
        self.assertEqual(self.find("MM-kvalifikatsioonimängud").league, "Muud võistlused")
        single = self.find("individuaal")
        self.assertEqual((single.level, single.end), (1, ""))

    def test_ignores_broken_input(self):
        self.assertEqual(adapter.parse('{"events": []}'), [])
        self.assertEqual(adapter.parse('{"events": [{"title": "X", "start_date": "?", "end_date": "?", "venue": {"country": "Eesti"}}]}'), [])

    def test_venues_known_and_group(self):
        cfg = config.load()
        venues = Venues.load()
        kept = build.only_estonia(self.events, venues, Geo(cfg))
        self.assertEqual(len(kept), 4)
        self.assertEqual(venues.unknown, set())
        self.assertEqual({e.city for e in kept}, {"Tallinn"})
        talialad = next(g for g in build.SPORT_GROUPS if g["key"] == "g:tali")
        self.assertEqual(talialad["sports"], ["suusatamine", "uisutamine", "kurling"])


if __name__ == "__main__":
    unittest.main()
