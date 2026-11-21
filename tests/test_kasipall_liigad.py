import unittest
from datetime import date, datetime
from pathlib import Path

from scrapers import kasipall_liigad as adapter
from scrapers.http import FetchError

FIX = Path(__file__).parent / "fixtures"
LEAGUES = {i: (FIX / f"kasipall_league_{i}.html").read_text(encoding="utf-8") for i in (359, 361, 362)}
PROTOCOL = (FIX / "kasipall_protocol.html").read_text(encoding="utf-8")
COMPS = [{"id": 359, "league": "Meistriliiga (mehed)"}, {"id": 361, "league": "Meistriliiga (naised)"},
         {"id": 362, "league": "Eesti karikas (mehed)"}]


class FakeFetcher:
    def __init__(self, fail_ids=()):
        self.urls = []
        self.fail_ids = fail_ids

    def get(self, url):
        self.urls.append(url)
        for i, page in LEAGUES.items():
            if url == adapter.league_url(i):
                return page
        if any(url.endswith(f"/protocol/{i}") for i in self.fail_ids):
            raise FetchError(url)
        return PROTOCOL


class KasipallTest(unittest.TestCase):
    def test_list_dedup(self):
        games = adapter.parse_list(LEAGUES[359])
        self.assertEqual(len(games), 20)
        g = next(g for g in games if g["id"] == "9230")
        self.assertEqual((g["home"], g["away"]), ("Tallinna Mistra", "Põlva Serviti"))
        self.assertEqual(g["start"], datetime(2026, 11, 25, 19, 0))

    def test_other_competitions_and_suffix_strip(self):
        women = adapter.parse_list(LEAGUES[361])
        cup = adapter.parse_list(LEAGUES[362])
        self.assertEqual((len(women), len(cup)), (18, 6))
        self.assertIn("Käsipalliklubi Mella", {g["home"] for g in women})  # " N" eemaldatud
        self.assertIn("Tallinna Mistra", {g["home"] for g in cup})         # " K" eemaldatud
        self.assertIn("SK Tapa/Tapa valla Spordikool", {g["home"] for g in women})

    def test_results(self):
        games = adapter.parse_list(LEAGUES[359])
        played = {g["id"]: g["result"] for g in games if g["result"]}
        self.assertEqual(played["9223"], "24-33")  # HC Viimsi/Alexela, 28.10.2026
        self.assertTrue(all(g["result"] == "" for g in games if g["start"].year == 2027))
        self.assertGreater(len(played), 5)
        self.assertLess(len(played), len(games))
        e = adapter.to_event(next(g for g in games if g["id"] == "9223"), "Saal", "Meistriliiga")
        self.assertEqual(e.result, "24-33")

    def test_entities_unescaped(self):
        self.assertIn("HC Kehra/Horizon Pulp&Paper", {g["home"] for g in adapter.parse_list(LEAGUES[359])})

    def test_venue_from_protocol(self):
        self.assertEqual(adapter.parse_venue(PROTOCOL), "Viimsi kooli Spordikeskus")

    def test_fetch_only_window_protocols(self):
        f = FakeFetcher()
        events = adapter.fetch(f, source={"competitions": COMPS}, today=date(2026, 11, 20))
        self.assertEqual(len(events), 44)
        protocol_calls = [u for u in f.urls if "/protocol/" in u]
        # 20.11–05.12: meeste liigas 7 mängu + naiste liigas 1 (04.12 HC Tabasalu – Mistra)
        self.assertEqual(len(protocol_calls), 8)
        self.assertEqual({e.league for e in events}, {c["league"] for c in COMPS})

    def test_home_field_fallback_when_protocol_has_no_venue(self):
        team = (FIX / "kasipall_team_826.html").read_text(encoding="utf-8")
        self.assertEqual(adapter.parse_home_field(team), "Kristiine Spordihall")

        class NoVenueFetcher(FakeFetcher):
            def get(self, url):
                self.urls.append(url)
                if url == adapter.league_url(361):
                    return LEAGUES[361]
                if "/team/" in url:
                    return team
                return "<html>protokoll ilma saalita</html>"

        f = NoVenueFetcher()
        events = adapter.fetch(f, source={"competitions": [COMPS[1]]}, today=date(2027, 1, 10))
        mella_home = next(e for e in events if e.home == "Käsipalliklubi Mella" and e.start.day == 13)
        self.assertEqual(mella_home.venue, "Kristiine Spordihall")
        team_calls = [u for u in f.urls if "/team/" in u]
        self.assertEqual(len(team_calls), len(set(team_calls)))  # iga meeskonna leht ainult korra

    def test_one_failed_protocol_does_not_break(self):
        with self.assertLogs("scrapers.kasipall_liigad", "WARNING"):
            events = adapter.fetch(FakeFetcher(fail_ids=["9230"]), source={"competitions": COMPS[:1]},
                                   today=date(2026, 11, 20))
        self.assertEqual(next(e for e in events if e.url.endswith("/9230")).venue, "")


if __name__ == "__main__":
    unittest.main()
