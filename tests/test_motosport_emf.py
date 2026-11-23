import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, motosport_emf as adapter
from scrapers.geo import Geo
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "motosport_emf.ics"


class MotosportEmfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = next(s for s in config.load()["source"] if s["name"] == "motosport_emf")
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"), cls.source, date(2026, 3, 1))

    def find(self, title):
        return next(e for e in self.events if e.home == title)

    def test_all_day_timezone_bug(self):
        # iCal: DTSTART:20261205T200000Z (pluginal viga) → tegelik päev 6.12, ilma kellaajata
        e = self.find("Adrenalin Arena Cup I etapp 26/27")
        self.assertEqual(e.start.date(), date(2026, 12, 6))
        self.assertTrue(e.time_tbc)
        self.assertEqual(e.end, "")
        self.assertEqual((e.sport, e.league, e.level, e.away), ("motosport", "Motokross", 1, ""))
        self.assertEqual(e.url, "https://msport.ee/events/adrenalin-arena-cup-i-etapp-26-27/")

    def test_multi_day_and_venue_from_title(self):
        e = self.find("SuperCross Tallinn 2026")
        self.assertEqual((e.start.date(), e.end), (date(2026, 11, 13), "2026-11-14"))
        self.assertEqual(e.venue, "Saku Suurhall")
        self.assertEqual(self.find("Adrenalin Arena Cup I etapp 26/27").venue, "Adrenalin Arena")
        # pikem märksõna enne: "Äksi jäärada … Saadjärve" → Saadjärve
        self.assertEqual(self.find("Äksi jäärada II etapp 2026- Saadjärve").venue, "Saadjärve")

    def test_skipped(self):
        titles = {e.home for e in self.events}
        for t in ("Supercross Tallinn 2026 “Avatud trennipäev”",                 # trennipäev
                  "Eesti Mootorrattaspordi Föderatsiooni hooajalõpu Gala 2026",   # gala
                  "Motokrossi korraldajate ja kohtunike koolitus 2026",           # koolitus
                  "Supermoto EMV I etapp Madona (Läti) 2026",                     # välismaal
                  "Vidriži Enduro EMV/EKV 2026 (LV)",
                  "Rannu mäkketõus EMV III etapp 2026- TÜHISTATUD!"):
            self.assertNotIn(t, titles)
        self.assertTrue(all(e.start.date() >= date(2025, 12, 31) for e in self.events))  # vanu aastaid ei loeta

    def test_levels(self):
        self.assertEqual(self.find("ENKV 3. etapp Valga 2026").level, 4)
        self.assertEqual(self.find("Pärnu Särtsukad III etapp").level, 4)
        self.assertEqual(self.find("KTL klubi I etapp 2026").level, 3)

    def test_hinted_venues_known(self):
        venues = Venues.load()
        geo = Geo(config.load())
        for name in set(self.source["venue_hints"].values()):
            v = venues.lookup(name)
            self.assertIsNotNone(v, name)
            self.assertTrue(geo.is_estonian(v.city), v.city)
        kept = build.only_estonia([e for e in self.events if e.venue], venues, geo)
        self.assertEqual(len(kept), len([e for e in self.events if e.venue]))


if __name__ == "__main__":
    unittest.main()
