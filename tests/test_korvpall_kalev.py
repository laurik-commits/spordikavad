import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config, korvpall_kalev as adapter
from scrapers.geo import Geo
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIXTURE = Path(__file__).parent / "fixtures" / "korvpall_kalev.html"


class KorvpallKalevTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = adapter.parse(FIXTURE.read_text(encoding="utf-8"))

    def find(self, slug):
        return next(e for e in self.events if e.url == f"https://bckalev.ee/event/{slug}/")

    def test_count(self):
        self.assertEqual(len(self.events), 22)

    def test_home_game(self):
        e = self.find("bigbank-kalev-vs-manchester-basketball-2")
        self.assertEqual((e.home, e.away), ("Bigbank/Kalev", "Manchester Basketball"))
        self.assertEqual(e.start, datetime(2026, 12, 15, 19, 30, tzinfo=TALLINN))
        self.assertEqual(e.league, "FIBA Europe Cup")
        self.assertEqual(e.venue, "Kalevi spordihall")
        self.assertEqual(e.sport, "korvpall")

    def test_vs_order_is_home_first(self):
        e = self.find("keila-kk-vs-bigbank-kalev-2")  # Keila KK koduväljak
        self.assertEqual((e.home, e.away, e.venue), ("Keila KK", "Bigbank/Kalev", "Keila Tervisekeskus"))
        p = self.find("bc-parnu-vs-bigbank-kalev")
        self.assertEqual((p.home, p.venue), ("BC Pärnu", "Pärnu Spordihoone"))

    def test_results_page_gives_scores(self):
        page = (Path(__file__).parent / "fixtures" / "korvpall_kalev_tulemused.html").read_text(encoding="utf-8")
        games = adapter.parse(page)
        played = [e for e in games if e.result]
        self.assertEqual((len(games), len(played)), (20, 19))
        e = next(e for e in played if e.start.day == 17 and e.start.month == 11)
        self.assertEqual((e.home, e.away, e.result), ("Bigbank/Kalev", "Valmiera Glass VIA", "83-81"))
        self.assertTrue(e.url.startswith("https://bckalev.ee/event/"))  # mängu leht = seis ja statistika
        # ajakava lehel tulemuste veergu pole
        self.assertTrue(all(g.result == "" for g in self.events))
        v = Venues.load()
        self.assertEqual({g.venue for g in played if g.venue and v.lookup(g.venue) is None}, set())

    def test_season_start(self):
        from datetime import date
        self.assertEqual(adapter.season_start(date(2026, 11, 22)), date(2026, 8, 1))
        self.assertEqual(adapter.season_start(date(2027, 3, 1)), date(2026, 8, 1))
        self.assertEqual(adapter.season_start(date(2027, 8, 2)), date(2027, 8, 1))

    def test_fetch_takes_only_played_games_of_this_season_and_survives_failure(self):
        from datetime import date
        from scrapers.http import FetchError
        schedule = FIXTURE.read_text(encoding="utf-8")
        results = (Path(__file__).parent / "fixtures" / "korvpall_kalev_tulemused.html").read_text(encoding="utf-8")

        class F:
            def __init__(self, fail):
                self.fail = fail

            def get(self, url):
                if url.endswith("/tulemused/"):
                    if self.fail:
                        raise FetchError("x")
                    return results
                return schedule

        both = adapter.fetch(F(False), today=date(2026, 11, 22))
        self.assertEqual(len(both), len(self.events) + 19)  # tulemuste lehelt ainult mängitud mängud
        self.assertEqual(len(adapter.fetch(F(True), today=date(2026, 11, 22))), len(self.events))
        # järgmisel hooajal ei võeta eelmise hooaja mänge
        self.assertEqual(len(adapter.fetch(F(False), today=date(2027, 8, 2))), len(self.events))

    def test_missing_venue(self):
        self.assertEqual(self.find("vef-riga-vs-bigbank-kalev").venue, "")           # tühi väli
        self.assertEqual(self.find("bigbank-kalev-vs-vef-riga").venue, "")           # "Asukoht selgumisel"
        self.assertEqual(sum(1 for e in self.events if not e.venue), 5)

    def test_html_entities(self):
        e = self.find("bigbank-kalev-vs-tartu-ulikool-maksmoorits")
        self.assertEqual(e.away, "Tartu Ülikool Maks&Moorits")

    def test_leagues(self):
        self.assertEqual({e.league for e in self.events}, {"Eesti-Läti Korvpalliliiga", "FIBA Europe Cup"})

    def test_geo_filter_keeps_only_estonian_games(self):
        entry = {}
        kept = build.only_estonia(self.events, Venues.load(), Geo(config.load()), date(2026, 11, 20), entry)
        self.assertEqual(len(kept), 13)  # 22 - 5 ilma saalita - 4 välismaal (Kosovo, Valmiera, Riga Arena, KSSH)
        self.assertNotIn("Kosovo", {e.venue for e in kept})
        self.assertEqual({e.venue for e in kept}, {"Keila Tervisekeskus", "Nord Spordihoone", "Kalevi spordihall",
                                                   "TalTechi spordihall", "Saku Suurhall", "Pärnu Spordihoone"})
        # lähipäevade mäng ilma saalita (VEF Riga 21.11) tuleb "ilma toimumiskohata" aruandesse
        self.assertEqual(len(entry["no_venue"]), 1)

    def test_unique_ids(self):
        self.assertEqual(len({e.id for e in self.events}), len(self.events))


if __name__ == "__main__":
    unittest.main()
