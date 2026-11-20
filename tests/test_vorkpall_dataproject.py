import unittest
from datetime import datetime
from pathlib import Path

from scrapers import config
from scrapers import vorkpall_dataproject as adapter
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIX = Path(__file__).parent / "fixtures"

COMPS = {c["league"]: c for c in next(s for s in config.load()["source"] if s["name"] == adapter.NAME)["competitions"]}
FILES = {
    "Balti liiga (mehed)": "vorkpall_bvl_mehed.html",
    "Balti liiga (naised)": "vorkpall_bvl_naised.html",
    "Meistriliiga (mehed)": "vorkpall_evf_mehed_emv.html",
    "Meistriliiga (naised)": "vorkpall_evf_naised_ml.html",
    "Eesti karikas (mehed)": "vorkpall_evf_mehed_karikas.html",
    "Eesti karikas (naised)": "vorkpall_evf_naised_karikas.html",
}


def parse(league):
    return adapter.parse((FIX / FILES[league]).read_text(encoding="utf-8"), COMPS[league])


class FakeFetcher:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        league = next(l for l, c in COMPS.items() if url == adapter.matches_url(c))
        return (FIX / FILES[league]).read_text(encoding="utf-8")


class VorkpallDataprojectTest(unittest.TestCase):
    def test_counts_per_competition(self):
        counts = {l: len(parse(l)) for l in FILES}
        self.assertEqual(counts, {
            "Balti liiga (mehed)": 38, "Balti liiga (naised)": 42, "Meistriliiga (mehed)": 0,
            "Meistriliiga (naised)": 19, "Eesti karikas (mehed)": 16, "Eesti karikas (naised)": 9,
        })

    def test_mens_baltic_home_game(self):
        e = next(e for e in parse("Balti liiga (mehed)") if e.home == "Audentes/Solarstone" and e.away == "Barrus Võru VK")
        self.assertEqual(e.start, datetime(2026, 11, 27, 19, 0, tzinfo=TALLINN))
        self.assertEqual(e.url, "https://bvl-web.dataproject.com/MatchStatistics.aspx?mID=1659&ID=29&PID=30")

    def test_womens_league_game_in_tallinn(self):
        e = next(e for e in parse("Meistriliiga (naised)") if e.home == "TalTech/Nordaid")
        self.assertEqual(e.league, "Meistriliiga (naised)")
        self.assertTrue(e.url.startswith("https://evf-web.dataproject.com/MatchStatistics.aspx?mID="))
        self.assertTrue(e.url.endswith("&ID=97&PID=147"))

    def test_url_without_pid(self):
        self.assertEqual(adapter.matches_url(COMPS["Meistriliiga (mehed)"]),
                         "https://evf-web.dataproject.com/CompetitionMatches.aspx?ID=96")

    def test_fetch_uses_all_configured_competitions(self):
        f = FakeFetcher()
        src = {"competitions": list(COMPS.values())}
        events = adapter.fetch(f, source=src)
        self.assertEqual(len(f.urls), 6)
        self.assertEqual(len(events), 124)
        self.assertEqual(len({e.id for e in events}), 124)

    def test_all_venues_known(self):
        v = Venues.load()
        unknown = {e.venue for l in FILES for e in parse(l) if v.lookup(e.venue) is None}
        self.assertEqual(unknown, set())

    def test_no_markup_in_team_names(self):
        self.assertFalse(any("<" in e.home + e.away for l in FILES for e in parse(l)))


if __name__ == "__main__":
    unittest.main()
