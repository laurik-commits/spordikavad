import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config, jaahoki_vipers as adapter
from scrapers.geo import Geo
from scrapers.model import TALLINN, new_event
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "jaahoki_vipers.html"


class JaahokiVipersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = FIXTURE.read_text(encoding="utf-8")
        cls.events = adapter.parse(cls.page)

    def test_only_unibet_home_games(self):
        # lehel 132 mängu (iga mäng kahes vaates), Unibet meeskonnal 10, neist 6 kodumängu; noored jäävad välja
        self.assertEqual(len(self.events), 6)
        self.assertEqual({e.home for e in self.events}, {"HC Vipers"})
        self.assertEqual({(e.league, e.level) for e in self.events}, {("Unibet Hokiliiga", 1)})
        self.assertNotIn("Viru Sputnik", {e.home for e in self.events})   # võõrsil mäng (koht lehel vale)

    def test_home_game(self):
        e = next(e for e in self.events if e.start.date() == date(2026, 11, 28))
        self.assertEqual(e.start, datetime(2026, 11, 28, 16, 35, tzinfo=TALLINN))
        self.assertEqual(e.away, "HC Everest")
        self.assertEqual(e.sport, "jaahoki")
        self.assertFalse(e.time_tbc)
        self.assertEqual(e.result, "")
        self.assertTrue(e.url.startswith("https://ehs.eestihoki.ee/statistika/maengu-aruanne/?divisionId=21573&gameId="))

    def test_missing_time_and_link(self):
        row = ('<article class="gc10-game-row" data-team="unibet" data-month="2027-03" data-date="2027-03-06" '
               'data-title="HC Vipers Unibet &mdash; Narva PSK"><div class="gc10-date-box"><b>6</b><span>MAR</span>'
               '<small>—</small></div><div class="gc10-venue"><span class="gc10-pin">⌖</span><span>Tondiraba Jäähall'
               '</span></div><div class="gc10-action"></div></article>')
        e, = adapter.parse(row)
        self.assertTrue(e.time_tbc)
        self.assertEqual(e.url, adapter.URL)
        self.assertEqual((e.home, e.away), ("HC Vipers", "Narva PSK"))

    def test_geo_filter_keeps_games_in_tondiraba(self):
        entry = {}
        kept = build.only_estonia(self.events, Venues.load(), Geo(config.load()), date(2026, 11, 22), entry)
        self.assertEqual(len(kept), 6)
        self.assertEqual({(e.venue, e.city) for e in kept}, {("Tondiraba jäähall", "Tallinn")})

    def test_manual_entry_is_deduped(self):
        # sama mäng käsitsi lisatuna (kasitsi.toml); automaatne allikas on config.toml-is eespool ja jääb alles
        manual = new_event(source="kasitsi", sport="jaahoki", league="Unibet Hokiliiga",
                           start=datetime(2026, 11, 28, 16, 35), home="HC Vipers", away="HC Everest",
                           venue="Tondiraba jäähall", city="", url="https://hcvipers.ee/")
        venues, geo = Venues.load(), Geo(config.load())
        kept, removed = build.dedupe(build.only_estonia(self.events + [manual], venues, geo))
        self.assertEqual(removed, 1)
        self.assertEqual([e.source for e in kept if e.start.date() == date(2026, 11, 28)], [adapter.NAME])

    def test_source_order_before_manual(self):
        names = [s["name"] for s in config.load()["source"]]
        self.assertLess(names.index(adapter.NAME), names.index("kasitsi"))

    def test_unique_ids(self):
        self.assertEqual(len({e.id for e in self.events}), len(self.events))


if __name__ == "__main__":
    unittest.main()
