import unittest
from datetime import date, datetime
from pathlib import Path

from scrapers import jalgpall_ejl as adapter
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIX = Path(__file__).parent / "fixtures"
MEN = (FIX / "jalgpall_premiumliiga.html").read_text(encoding="utf-8")
WOMEN = (FIX / "jalgpall_naiste_ml.html").read_text(encoding="utf-8")


class FakeFetcher:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return MEN if "/52/" in url else WOMEN


class JalgpallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.men = adapter.parse(MEN, "Premium liiga")
        cls.women = adapter.parse(WOMEN, "Naiste meistriliiga")

    def test_full_seasons(self):
        self.assertEqual(len(self.men), 180)  # 10 võistkonda, 36 vooru
        self.assertEqual(len(self.women), 75)

    def test_first_game(self):
        e = next(e for e in self.men if e.url.endswith("/match_info/186106"))
        self.assertEqual((e.home, e.away), ("Tallinna FC Flora", "FC Nõmme United"))
        self.assertEqual(e.start, datetime(2026, 3, 7, 12, 30, tzinfo=TALLINN))
        self.assertEqual(e.venue, "Sportland Arena")
        self.assertEqual(e.league, "Premium liiga")

    def test_results_are_read(self):
        e = next(e for e in self.men if e.url.endswith("/match_info/186106"))
        self.assertEqual(e.result, "3-0")
        self.assertTrue(all(g.result for g in self.men))  # kogu hooaeg on mängitud
        self.assertTrue(all(g.result for g in self.women))

    def test_unplayed_game_has_no_result(self):
        page = MEN.replace("3 - 0</a>", "-</a>", 1)
        e = next(e for e in adapter.parse(page, "Premium liiga") if e.url.endswith("/match_info/186106"))
        self.assertEqual(e.result, "")

    def test_all_venues_known_and_tallinn_share(self):
        v = Venues.load()
        self.assertEqual([e.venue for e in self.men + self.women if v.lookup(e.venue) is None], [])
        self.assertEqual(sum(v.is_tallinn(e.venue) for e in self.men), 72)
        self.assertEqual(sum(v.is_tallinn(e.venue) for e in self.women), 12)

    def test_fetch_all_competitions_for_current_year(self):
        f = FakeFetcher()
        src = {"competitions": [{"id": 52, "league": "Premium liiga"}, {"id": 63, "league": "Naiste meistriliiga"}]}
        events = adapter.fetch(f, source=src, today=date(2027, 3, 1))
        self.assertEqual(f.urls, [adapter.url_for(52, 2027), adapter.url_for(63, 2027)])
        self.assertEqual(len(events), 255)
        self.assertTrue(adapter.url_for(63, 2027).endswith("/voistlused/63/liigad/calendar?season=2027"))


if __name__ == "__main__":
    unittest.main()
