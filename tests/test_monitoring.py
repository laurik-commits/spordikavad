"""Vaikse lagunemise kontrollid: hooajad, tulevaste mängude kontroll, saalita mängud, salvestus."""

import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import build
from scrapers import config
from scrapers.model import new_event


def ev(when, league="Liiga", venue="Haabersti jäähall"):
    return new_event(source="t", sport="jaahoki", league=league, start=when, home="A", away="B",
                     venue=venue, city="", url="https://example.org/x")


class SeasonTest(unittest.TestCase):
    def test_recurring_season_over_new_year(self):
        src = {"seasons": [["09-15", "05-15"]]}
        self.assertTrue(config.in_season(src, date(2026, 11, 20)))
        self.assertTrue(config.in_season(src, date(2031, 2, 1)))   # töötab ka aastate pärast
        self.assertFalse(config.in_season(src, date(2027, 7, 1)))

    def test_recurring_season_within_year_and_full_dates(self):
        self.assertTrue(config.in_season({"seasons": [["03-01", "11-15"]]}, date(2029, 6, 1)))
        self.assertFalse(config.in_season({"seasons": [["03-01", "11-15"]]}, date(2029, 12, 1)))
        self.assertTrue(config.in_season({"seasons": [["2026-01-01", "2026-12-31"]]}, date(2026, 5, 5)))

    def test_competition_inherits_source_season(self):
        src = {"seasons": [["09-15", "05-15"]]}
        self.assertTrue(config.in_season({}, date(2026, 11, 20), src))
        self.assertFalse(config.in_season({"seasons": [["03-01", "04-01"]]}, date(2026, 11, 20), src))

    def test_config_has_no_absolute_season_dates(self):
        for s in config.load()["source"]:
            for start, end in s["seasons"]:
                self.assertEqual((len(start), len(end)), (5, 5), f"{s['name']}: kasuta MM-DD")


class MissingUpcomingTest(unittest.TestCase):
    SRC = {"name": "x", "seasons": [["09-01", "05-31"]],
           "competitions": [{"league": "A"}, {"league": "B"}, {"league": "Karikas", "check": False}]}
    TODAY = date(2026, 11, 20)

    def test_league_with_only_past_games_is_flagged(self):
        # B-l on ainult eelmise hooaja / möödunud mängud → see on "vaikselt kadunud" liiga
        fetched = [ev(datetime(2026, 11, 25, 19), "A"), ev(datetime(2026, 3, 1, 19), "B")]
        self.assertEqual(build.missing_upcoming(self.SRC, fetched, self.TODAY), ["B"])

    def test_cups_not_checked_and_offseason_ignored(self):
        fetched = [ev(datetime(2026, 11, 25, 19), "A"), ev(datetime(2026, 12, 1, 19), "B")]
        self.assertEqual(build.missing_upcoming(self.SRC, fetched, self.TODAY), [])
        self.assertEqual(build.missing_upcoming(self.SRC, [], date(2026, 7, 1)), [])

    def test_winter_break_within_window(self):
        fetched = [ev(datetime(2027, 1, 10, 19), "A"), ev(datetime(2027, 1, 12, 19), "B")]
        self.assertEqual(build.missing_upcoming(self.SRC, fetched, date(2026, 12, 5)), [])

    def test_source_without_competitions(self):
        src = {"name": "hoki", "league": "Hokiliiga", "seasons": [["09-01", "03-31"]]}
        self.assertEqual(build.missing_upcoming(src, [ev(datetime(2026, 3, 1, 18))], self.TODAY), ["Hokiliiga"])


class NoVenueTest(unittest.TestCase):
    def test_games_without_venue_are_reported_only_in_window(self):
        from scrapers.geo import Geo
        from scrapers.venues import Venues
        entry = {}
        events = [ev(datetime(2026, 11, 25, 19), venue=""), ev(datetime(2027, 2, 1, 19), venue=""),
                  ev(datetime(2026, 11, 25, 18))]
        kept = build.only_estonia(events, Venues.load(), Geo(config.load()), date(2026, 11, 20), entry)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(entry["no_venue"]), 1)
        self.assertIn("25.11 19:00 A – B", entry["no_venue"][0])


class SaveTest(unittest.TestCase):
    def test_unchanged_data_is_not_rewritten(self):
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(build, "DATA", tmp):
            e = [ev(datetime(2026, 11, 25, 19))]
            build.save("x", e)
            first = (tmp / "x.json").read_text(encoding="utf-8")
            with mock.patch.object(build, "datetime", wraps=datetime) as dt:
                dt.now.return_value = datetime(2030, 1, 1)
                build.save("x", e)
            self.assertEqual((tmp / "x.json").read_text(encoding="utf-8"), first)
            build.save("x", e + [ev(datetime(2026, 11, 26, 19))])
            self.assertEqual(len(json.loads((tmp / "x.json").read_text(encoding="utf-8"))["events"]), 2)


if __name__ == "__main__":
    unittest.main()
