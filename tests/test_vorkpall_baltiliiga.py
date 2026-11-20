import unittest
from datetime import datetime
from pathlib import Path

from scrapers import vorkpall_baltiliiga as adapter
from scrapers.model import TALLINN

FIXTURE = Path(__file__).parent / "fixtures" / "vorkpall_baltiliiga.html"


class VorkpallBaltiliigaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def test_count_skips_postponed(self):
        self.assertEqual(len(self.events), 38)
        self.assertEqual(len({e.id for e in self.events}), 38)

    def test_tallinn_home_game(self):
        e = next(e for e in self.events if e.home == "Audentes/Solarstone" and e.away == "Barrus Võru VK")
        self.assertEqual(e.start, datetime(2026, 11, 27, 19, 0, tzinfo=TALLINN))
        self.assertEqual(e.venue, "Audentese Sports Hall")
        self.assertIn("MatchStatistics.aspx?mID=", e.url)

    def test_bold_winner_markup_stripped(self):
        self.assertFalse(any("<" in e.home or "<" in e.away for e in self.events))


if __name__ == "__main__":
    unittest.main()
