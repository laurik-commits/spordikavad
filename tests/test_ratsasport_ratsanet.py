import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, ratsasport_ratsanet as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "ratsasport_ratsanet.html"


class RatsasportRatsanetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def find(self, title):
        return next(e for e in self.events if e.home == title)

    def test_foreign_and_cancelled_dropped(self):
        # 75 rida: välja jäävad välismaa (ESP, BEL, ITA) ja tühistatud võistlus
        self.assertEqual(len(self.events), 66)
        titles = {e.home for e in self.events}
        self.assertNotIn("Kukulinna Karikas koolisõidus", titles)   # tühistatud
        self.assertFalse(any(e.venue in ("Oliva", "Lier") for e in self.events))

    def test_dates(self):
        self.assertEqual(adapter.parse_dates("03. - 08. november 2026"), (date(2026, 11, 3), date(2026, 11, 8)))
        self.assertEqual(adapter.parse_dates("30. aprill 2027 - 02. mai 2027"), (date(2027, 4, 30), date(2027, 5, 2)))
        self.assertEqual(adapter.parse_dates("16. jaanuar 2027"), (date(2027, 1, 16), None))
        self.assertEqual(adapter.parse_dates("30. - 02. jaanuar 2027"), (date(2026, 12, 30), date(2027, 1, 2)))

    def test_event_row(self):
        e = self.find("Jõuluootus Toomingal")
        self.assertEqual((e.sport, e.away, e.venue), ("ratsasport", "", "Toominga tall"))
        self.assertEqual((e.start.date(), e.end), (date(2026, 11, 28), "2026-11-29"))
        self.assertEqual(e.league, "Koolisõit, Parakoolisõit")
        self.assertEqual(e.url, "https://ratsanet.ee/events/4642")
        self.assertTrue(e.time_tbc)

    def test_levels(self):
        self.assertEqual(self.find("CHI Pärnu takistussõit 1 (CSI2 projekt)").level, 1)   # rahvusvaheline
        self.assertEqual(self.find("Toominga Koolisõit SMV").level, 1)                     # Eesti SMV
        self.assertEqual(self.find("Gramina Jõulud").level, 1)                             # takistused kuni 130 cm
        self.assertEqual(self.find("THK Talvekarikas 2026").level, 3)                      # 70-110 cm, klubi
        self.assertEqual(self.find("Ihaste takistussõit / Tartu linna SMV").level, 3)      # linna MV
        self.assertEqual(self.find("Ihaste sisekolmevõistlus / Juunioride ja seenioride SMV / Tartu linna SMV").level, 1)

    def test_venues(self):
        venues = Venues.load()
        kept = build.only_estonia(self.events, venues, Geo(config.load()))
        # Varssav on välismaa (geo.foreign), kõik Eesti kohad on teada
        self.assertEqual(venues.unknown, set())
        self.assertNotIn("Varssav", {e.venue for e in kept})
        self.assertEqual({e.city for e in kept if e.venue == "Tori Hobusekasvandus"}, {"Tori"})


if __name__ == "__main__":
    unittest.main()
