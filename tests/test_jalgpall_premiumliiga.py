import unittest
from datetime import date, datetime
from pathlib import Path

from scrapers import jalgpall_premiumliiga as adapter
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "jalgpall_premiumliiga.html"


class JalgpallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def test_full_season(self):
        self.assertEqual(len(self.events), 180)  # 10 võistkonda, 36 vooru
        self.assertEqual(len({e.id for e in self.events}), 180)

    def test_first_game(self):
        e = next(e for e in self.events if e.url.endswith("/match_info/186106"))
        self.assertEqual((e.home, e.away), ("Tallinna FC Flora", "FC Nõmme United"))
        self.assertEqual(e.start, datetime(2026, 3, 7, 12, 30, tzinfo=TALLINN))
        self.assertEqual(e.venue, "Sportland Arena")

    def test_all_venues_known_and_tallinn_share(self):
        v = Venues.load()
        self.assertEqual([e.venue for e in self.events if v.lookup(e.venue) is None], [])
        self.assertEqual(sum(v.is_tallinn(e.venue) for e in self.events), 72)

    def test_season_url_follows_year(self):
        self.assertTrue(adapter.url_for(date(2027, 3, 1).year).endswith("season=2027"))


if __name__ == "__main__":
    unittest.main()
