import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

from scrapers import saalihoki_meistriliiga as adapter
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "saalihoki_meistriliiga.html"


class SaalihokiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def test_only_selected_leagues(self):
        counts = Counter(e.league for e in self.events)
        self.assertEqual(counts["Meistriliiga (mehed)"], 4)
        self.assertEqual(counts["Eesti-Läti liiga (mehed)"], 14)
        self.assertEqual(counts["Eesti-Läti liiga (naised)"], 19)
        self.assertEqual(sum(counts.values()), len(self.events))  # noored, M35+ jm välja

    def test_missing_space_before_dash(self):
        e = next(e for e in self.events if e.url.endswith("id=8735"))
        self.assertEqual((e.home, e.away), ("Jõgeva SK Tähe/Olivia", "FBK SĀC"))

    def test_tallinn_game(self):
        e = next(e for e in self.events if e.url.endswith("id=8700"))
        self.assertEqual(e.start, datetime(2026, 12, 12, 14, 30, tzinfo=TALLINN))
        self.assertTrue(Venues.load().is_tallinn(e.venue))
        # pistekontrollis leitud viga: link peab olema /Events/ kaustas (muidu 404)
        self.assertEqual(e.url, "https://www.saalihoki.ee/Events/Uritus.aspx?id=8700")

    def test_all_venues_known(self):
        v = Venues.load()
        self.assertEqual([e.venue for e in self.events if v.lookup(e.venue) is None], [])


if __name__ == "__main__":
    unittest.main()
