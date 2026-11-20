import unittest
from datetime import date, datetime
from pathlib import Path

from scrapers import kasipall_meistriliiga as adapter
from scrapers.http import FetchError

FIX = Path(__file__).parent / "fixtures"
LEAGUE = (FIX / "kasipall_league.html").read_text(encoding="utf-8")
PROTOCOL = (FIX / "kasipall_protocol.html").read_text(encoding="utf-8")


class FakeFetcher:
    def __init__(self, fail_ids=()):
        self.urls = []
        self.fail_ids = fail_ids

    def get(self, url):
        self.urls.append(url)
        if url == adapter.URL:
            return LEAGUE
        if any(url.endswith(f"/protocol/{i}") for i in self.fail_ids):
            raise FetchError(url)
        return PROTOCOL


class KasipallTest(unittest.TestCase):
    def test_list_dedup(self):
        games = adapter.parse_list(LEAGUE)
        self.assertEqual(len(games), 20)
        g = next(g for g in games if g["id"] == "9230")
        self.assertEqual((g["home"], g["away"]), ("Tallinna Mistra", "Põlva Serviti"))
        self.assertEqual(g["start"], datetime(2026, 11, 25, 19, 0))

    def test_entities_unescaped(self):
        self.assertIn("HC Kehra/Horizon Pulp&Paper", {g["home"] for g in adapter.parse_list(LEAGUE)})

    def test_venue_from_protocol(self):
        self.assertEqual(adapter.parse_venue(PROTOCOL), "Viimsi kooli Spordikeskus")

    def test_fetch_only_window_protocols(self):
        f = FakeFetcher()
        events = adapter.fetch(f, today=date(2026, 11, 20))
        self.assertEqual(len(events), 20)
        protocol_calls = [u for u in f.urls if "/protocol/" in u]
        # 20.11–05.12: 25.11 (3), 02.12 (2), 03.12, 05.12 = 7 mängu
        self.assertEqual(len(protocol_calls), 7)
        old = next(e for e in events if e.url.endswith("/protocol/9222"))
        self.assertEqual(old.venue, "")

    def test_one_failed_protocol_does_not_break(self):
        with self.assertLogs("scrapers.kasipall_meistriliiga", "WARNING"):
            events = adapter.fetch(FakeFetcher(fail_ids=["9230"]), today=date(2026, 11, 20))
        self.assertEqual(next(e for e in events if e.url.endswith("/9230")).venue, "")


if __name__ == "__main__":
    unittest.main()
