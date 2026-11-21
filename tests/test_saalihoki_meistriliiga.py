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


class FinishedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse_finished(
            (Path(__file__).parent / "fixtures" / "saalihoki_loppenud.html").read_text(encoding="utf-8"))

    def test_only_our_leagues_with_results(self):
        counts = Counter(e.league for e in self.events)
        # noored, M35+, Raplamaa jm on välja jäetud
        self.assertEqual(counts, {"Energialiiga": 5, "Eesti-Läti liiga (mehed)": 11, "Eesti-Läti liiga (naised)": 8})
        self.assertTrue(all(e.result for e in self.events))

    def test_game_fields(self):
        e = next(e for e in self.events if e.home == "Sparta Team Automaailm" and e.start.day == 14)
        self.assertEqual((e.away, e.result, e.league, e.level), ("Jõgeva SK Tähe / Olivia", "5-4",
                                                                  "Eesti-Läti liiga (mehed)", 1))
        self.assertEqual(e.start, datetime(2026, 11, 14, 16, 0, tzinfo=TALLINN))
        self.assertEqual(e.venue, "Märjamaa Valla Spordikeskus")
        # protokoll = seis ja statistika; link on täisaadress /Events/ kausta kõrval
        self.assertTrue(e.url.startswith("https://www.saalihoki.ee/Protokoll.aspx?id="))

    def test_energialiiga_is_level_two(self):
        self.assertEqual({e.level for e in self.events if e.league == "Energialiiga"}, {2})

    def test_nbsp_in_team_names_is_normalised(self):
        self.assertTrue(any(e.away == "FBK SĀC" or e.home == "FBK SĀC" for e in self.events))
        self.assertFalse(any("\xa0" in e.home + e.away for e in self.events))

    def test_all_venues_known(self):
        v = Venues.load()
        self.assertEqual([e.venue for e in self.events if v.lookup(e.venue) is None], [])

    def test_fetch_adds_finished_and_survives_failure(self):
        from scrapers.http import FetchError
        upcoming = FIXTURE.read_text(encoding="utf-8")
        finished = (Path(__file__).parent / "fixtures" / "saalihoki_loppenud.html").read_text(encoding="utf-8")

        class F:
            def __init__(self, fail):
                self.fail = fail

            def get(self, url):
                if url.endswith("Loppenud-mangud.aspx"):
                    if self.fail:
                        raise FetchError("x")
                    return finished
                return upcoming

        both = adapter.fetch(F(False))
        only_upcoming = adapter.fetch(F(True))
        self.assertEqual(len(both), len(only_upcoming) + len(self.events))
        self.assertEqual(len(only_upcoming), len(adapter.parse(upcoming)))


if __name__ == "__main__":
    unittest.main()
