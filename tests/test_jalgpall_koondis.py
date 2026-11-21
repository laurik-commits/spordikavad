import re
import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config, jalgpall_koondis as football, saalijalgpall_koondis as futsal
from scrapers.geo import Geo
from scrapers.model import TALLINN
from scrapers.venues import Venues

FX = Path(__file__).parent / "fixtures"


def load(name):
    return (FX / name).read_text(encoding="utf-8")


class JalgpallKoondisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.women = football.parse(load("jalgpall_koondis_naised.html"), "Naiste koondis")
        cls.futsal = futsal.parse(load("jalgpall_koondis_saal.html"), "Saalijalgpalli koondis")
        cls.nu19 = football.parse(load("jalgpall_koondis_nu19.html"), "NU19 koondis")

    def test_only_estonian_home_games(self):
        # naistel 8 mängu, neist 3 Eesti kodumängu (ülejäänud on võõrsil, kodumeeskond on vastane)
        self.assertEqual(len(self.women), 3)
        self.assertTrue(all(e.home == "Eesti" for e in self.women))

    def test_upcoming_game(self):
        e = next(e for e in self.women if e.start.date() == date(2026, 12, 1))
        self.assertEqual(e.start, datetime(2026, 12, 1, 18, 0, tzinfo=TALLINN))
        self.assertEqual((e.home, e.away, e.venue), ("Eesti", "Vastane selgumisel", "Paide jalgpallihall"))
        self.assertEqual(e.league, "Naiste koondis: Balti turniir 2026")
        self.assertEqual((e.sport, e.level, e.time_tbc), ("jalgpall", 5, False))
        self.assertEqual(e.url, "https://jalgpall.ee/koondis/7/matchinfo/match/4056")

    def test_futsal_has_own_sport_and_source(self):
        self.assertEqual({e.sport for e in self.futsal}, {"saalijalgpall"})
        self.assertEqual({e.source for e in self.futsal}, {"saalijalgpall_koondis"})
        self.assertEqual(len(self.futsal), 2)

    def test_foreign_venues_are_skipped(self):
        # NU19 mängud Ungaris on kirjas "Saal, Ungari" ja Eesti on seal formaalselt kodumeeskond
        self.assertEqual(len(self.nu19), 2)
        self.assertEqual({e.venue for e in self.nu19}, {"Tehvandi staadion"})

    def test_midnight_means_time_tbc(self):
        page = re.sub(r"(01\.12\.2026\s+kell\s+)18:00", r"\g<1>00:00", load("jalgpall_koondis_naised.html"))
        self.assertIn("00:00", page)
        e = next(e for e in football.parse(page, "Naiste koondis") if e.start.date() == date(2026, 12, 1))
        self.assertTrue(e.time_tbc)

    def test_unique_ids(self):
        every = self.women + self.futsal + self.nu19
        self.assertEqual(len({e.id for e in every}), len(every))

    def test_geo_filter_keeps_all_estonian_venues(self):
        entry = {}
        every = self.women + self.futsal + self.nu19
        kept = build.only_estonia(every, Venues.load(), Geo(config.load()), date(2026, 11, 20), entry)
        self.assertEqual(len(kept), len(every))
        self.assertNotIn("no_venue", entry)


if __name__ == "__main__":
    unittest.main()
