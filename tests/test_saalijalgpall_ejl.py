import unittest
from datetime import date, datetime
from pathlib import Path

from scrapers import saalijalgpall_ejl as adapter
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "saalijalgpall_2026.html"


class SaalijalgpallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"), "Saalijalgpalli meistriliiga")

    def test_count_and_sport(self):
        self.assertEqual(len(self.events), 45)
        self.assertEqual({e.sport for e in self.events}, {"saalijalgpall"})
        self.assertEqual({e.source for e in self.events}, {"saalijalgpall_ejl"})

    def test_prefix_stripped(self):
        self.assertFalse(any(e.home.startswith("S. ") or e.away.startswith("S. ") for e in self.events))
        e = next(e for e in self.events if e.start == datetime(2026, 11, 20, 19, 0, tzinfo=TALLINN))
        self.assertEqual((e.home, e.away), ("Jõhvi FC Phoenix", "Saku Sporting"))

    def test_venues_known_and_tallinn(self):
        v = Venues.load()
        self.assertEqual([e.venue for e in self.events if v.lookup(e.venue) is None], [])
        tallinn = [e for e in self.events if v.is_tallinn(e.venue)]
        self.assertEqual(len(tallinn), 6)
        self.assertTrue(all("Bunker" in e.home for e in tallinn))

    def test_season_start_year(self):
        self.assertEqual(adapter.season_for(date(2026, 11, 20)), 2026)
        self.assertEqual(adapter.season_for(date(2027, 2, 1)), 2026)
        self.assertEqual(adapter.season_for(date(2027, 9, 1)), 2027)


if __name__ == "__main__":
    unittest.main()
