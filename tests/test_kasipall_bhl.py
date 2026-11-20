import unittest
from datetime import datetime
from pathlib import Path

import build
from scrapers import config
from scrapers import kasipall_bhl as adapter
from scrapers.geo import Geo
from scrapers.model import TALLINN, new_event
from scrapers.venues import Venues

FIX = Path(__file__).parent / "fixtures"
COMPS = {c["id"]: c for c in next(s for s in config.load()["source"] if s["name"] == adapter.NAME)["competitions"]}


def parse(league_id):
    return adapter.parse((FIX / f"kasipall_bhl_{league_id}.html").read_text(encoding="utf-8"), COMPS[league_id])


class BalticHandballTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(parse(636)), 44)
        self.assertEqual(len(parse(637)), 36)

    def test_mistra_home_game(self):
        e = next(e for e in parse(636) if e.home == "Tallinna Mistra" and e.away == "HC Cocks")
        self.assertEqual(e.start, datetime(2026, 12, 5, 16, 0, tzinfo=TALLINN))
        self.assertEqual(e.venue, "Raasiku Spordihoone")
        self.assertEqual(e.league, "Balti liiga (mehed)")
        self.assertRegex(e.url, r"^https://baltichandball\.eu/season/206/league/636/game/\d+$")

    def test_year_from_month_header(self):
        jan = [e for e in parse(637) if e.start.month == 1]
        self.assertTrue(jan and all(e.start.year == 2027 for e in jan))

    def test_venues_known_or_blank(self):
        v = Venues.load()
        unknown = {e.venue for i in (636, 637) for e in parse(i) if e.venue and v.lookup(e.venue) is None}
        self.assertEqual(unknown, set())
        self.assertTrue(Venues.load().is_tallinn("Kristiine Sport"))
        geo = Geo(config.load())
        self.assertTrue(all(geo.is_known(x.city) for x in Venues.load().venues))

    def test_url(self):
        self.assertEqual(adapter.fixtures_url(COMPS[637]), "https://baltichandball.eu/season/206/league/637/fixtures")


class DedupeTest(unittest.TestCase):
    def test_same_game_from_two_sources_kept_once(self):
        def ev(source, home, league):
            return new_event(source=source, sport="kasipall", league=league, start=datetime(2026, 12, 5, 18, 0),
                             home=home, away="Viljandi HC/LEONHARD WEISS", venue="Mesikäpa hall", city="Põlva",
                             url="https://example.org/" + source)
        a = ev("kasipall_liigad", "Põlva Serviti", "Meistriliiga (mehed)")
        b = ev("kasipall_bhl", "Põlva  Serviti", "Balti liiga (mehed)")
        out, removed = build.dedupe([a, b])
        self.assertEqual((len(out), removed), (1, 1))
        self.assertEqual(out[0].source, "kasipall_liigad")  # esimene allikas jääb

    def test_different_team_names_same_hall_and_time(self):
        def ev(source, home, away):
            return new_event(source=source, sport="kasipall", league="L", start=datetime(2027, 1, 13, 19, 0),
                             home=home, away=away, venue="Kristiine spordihall", city="Tallinn",
                             url="https://example.org/" + source)
        out, removed = build.dedupe([ev("kasipall_liigad", "Käsipalliklubi Mella", "SK Tapa/Tapa valla Spordikool"),
                                     ev("kasipall_bhl", "KPK Mella", "SK Tapa")])
        self.assertEqual(removed, 1)
        # eri saalides samal ajal → kaks eri mängu
        other = new_event(source="x", sport="kasipall", league="L", start=datetime(2027, 1, 13, 19, 0),
                          home="A", away="B", venue="Tapa spordihoone", city="Tapa", url="https://example.org/y")
        self.assertEqual(len(build.dedupe([out[0], other])[0]), 2)


if __name__ == "__main__":
    unittest.main()
