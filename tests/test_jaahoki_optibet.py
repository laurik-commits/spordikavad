import unittest
from datetime import datetime
from pathlib import Path

from scrapers import jaahoki_optibet as adapter
from scrapers.model import TALLINN

FIXTURE = Path(__file__).parent / "fixtures" / "jaahoki_optibet.html"


class JaahokiOptibetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def test_count(self):
        self.assertEqual(len(self.events), 93)

    def test_panter_home_game(self):
        e = next(e for e in self.events if e.url.endswith("/hcp-kyc/20261121/35876"))
        self.assertEqual(e.home, "HC Panter")
        self.assertEqual(e.away, "HC Kyiv Capitals")
        self.assertEqual(e.start, datetime(2026, 11, 21, 18, 0, tzinfo=TALLINN))
        self.assertEqual(e.venue, "Tallina, Igaunija")
        self.assertEqual(e.sport, "jaahoki")
        self.assertFalse(e.time_tbc)
        self.assertTrue(e.url.startswith("https://www.lhf.lv/en/tournaments/"))

    def test_tba_times(self):
        tbc = [e for e in self.events if e.time_tbc]
        self.assertEqual(len(tbc), 3)
        self.assertTrue(all(e.start.hour == 0 for e in tbc))

    def test_unique_ids(self):
        self.assertEqual(len({e.id for e in self.events}), len(self.events))


if __name__ == "__main__":
    unittest.main()
