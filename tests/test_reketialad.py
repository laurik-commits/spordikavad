import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, sulgpall_esl, tennis_etl
from scrapers.geo import Geo
from scrapers.venues import Venues

FIX = Path(__file__).parent / "fixtures"


class TennisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = tennis_etl.parse((FIX / "tennis_etl.html").read_text(encoding="utf-8"))

    def find(self, title, day):
        return next(e for e in self.events if e.home == title and e.start.date() == day)

    def test_rows_years_and_levels(self):
        self.assertEqual(len(self.events), 36)
        gp = self.find("Eesti GP", date(2027, 1, 2))   # aasta tuleb pealkirjast „VÕISTLUSKALENDER 2027“
        self.assertEqual((gp.end, gp.level, gp.league, gp.venue), ("2027-01-04", 2, "Tennis: mehed ja naised", "Tallink City SK, Tallinn"))
        self.assertTrue(gp.time_tbc)
        self.assertEqual(self.find("Masters", date(2026, 11, 5)).level, 1)
        self.assertEqual(self.find("ITF Juniors Tallinn", date(2026, 11, 16)).level, 4)
        narva = self.find("Narva Cup TE14", date(2027, 1, 4))
        self.assertEqual((narva.level, narva.league, narva.venue), (4, "Tennis: tüdrukud ja poisid U14", "Top Spin, Narva"))
        self.assertEqual(self.find("Noorteliiga II", date(2027, 1, 2)).level, 3)   # osalemiseks: peidetud

    def test_typo_date_and_unique_ids(self):
        self.assertTrue(any(e.start.date() == date(2027, 1, 30) for e in self.events))   # „3o.01“
        self.assertEqual(len({e.id for e in self.events}), len(self.events))   # T18 ja P18 samal päeval eraldi

    def test_helpers(self):
        self.assertEqual(tennis_etl.league_of("P18"), "Tennis: poisid U18")
        self.assertEqual(tennis_etl.league_of("NLIITP"), "Tennis: noorteliiga")
        self.assertEqual(tennis_etl.level_of("Eesti MV", "M,N"), 1)
        self.assertEqual(tennis_etl.level_of("Eesti noorte MV", "T16"), 4)
        self.assertEqual(tennis_etl.venue_of("ETL", "Tallinn"), "Tallinn, koht täpsustamisel")


class SulgpallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = sulgpall_esl.parse((FIX / "sulgpall_esl.html").read_text(encoding="utf-8"))

    def by_title(self, title):
        return next(e for e in self.events if e.home == title)

    def test_levels_and_skips(self):
        self.assertEqual(len(self.events), 36)
        em = self.by_title("European Mixed Team Championships 2027")
        self.assertEqual((em.start.date(), em.end, em.level, em.venue), (date(2027, 1, 6), "2027-01-10", 1, "Kalevi Spordihall"))
        self.assertEqual(self.by_title("63. Eesti Meistrivõistlused").level, 1)
        self.assertEqual(self.by_title("Klubide Karikas 2026").level, 1)
        self.assertEqual(self.by_title("RSL GP-2").level, 2)
        self.assertEqual(self.by_title("RSL Estonian Junior 2026").level, 4)
        self.assertEqual(self.by_title("Eesti Noorte Meistrivõistlused 2026").level, 4)
        self.assertEqual(self.by_title("Victor Cup I").level, 3)
        titles = {e.home for e in self.events}
        self.assertFalse(titles & {"Baltic Senior Championships", "Seenior Open", "Paarissuled- edasi lükatud"})

    def test_dates_and_links(self):
        gp6 = self.by_title("RSL Noorte GP-6")   # „31. --- 01.11.2026“
        self.assertEqual((gp6.start.date(), gp6.end), (date(2026, 10, 31), "2026-11-01"))
        self.assertTrue(self.by_title("RSL Estonian Junior 2026").url.endswith("Invitation-RSL-Estonian-Junior-2026.pdf"))
        self.assertEqual(sulgpall_esl.dates_of("05.12.2026"), (date(2026, 12, 5), None))
        self.assertEqual(sulgpall_esl.dates_of("30.12. --- 02.01.2027"), (date(2026, 12, 30), date(2027, 1, 2)))


class RacketSetupTest(unittest.TestCase):
    def test_all_venues_known_and_in_estonia(self):
        venues, geo = Venues.load(), Geo(config.load())
        events = (tennis_etl.parse((FIX / "tennis_etl.html").read_text(encoding="utf-8"))
                  + sulgpall_esl.parse((FIX / "sulgpall_esl.html").read_text(encoding="utf-8")))
        bad = sorted({e.venue for e in events if not (venues.lookup(e.venue) and geo.is_estonian(venues.lookup(e.venue).city))})
        self.assertEqual(bad, [])

    def test_group_and_sources(self):
        group = next(g for g in build.SPORT_GROUPS if g["key"] == "g:reket")
        self.assertEqual(group["sports"], ["tennis", "sulgpall", "lauatennis"])
        names = {s["name"] for s in config.load()["source"]}
        self.assertTrue({"tennis_etl", "sulgpall_esl"} <= names)
        for sport in ("tennis", "sulgpall", "lauatennis"):
            self.assertIn(sport, build.SPORT_IN)
            self.assertIn(sport, build.SOURCE_SITES)
        css = (Path(__file__).parent.parent / "site" / "style.css").read_text(encoding="utf-8")
        for sport in ("tennis", "sulgpall", "lauatennis"):
            self.assertIn(f".s-{sport} {{", css)


if __name__ == "__main__":
    unittest.main()
