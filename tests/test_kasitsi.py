import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import build
from scrapers import config, kasitsi
from scrapers.geo import Geo
from scrapers.model import TALLINN
from scrapers.venues import Venues

GOOD = '''
[[event]]
sport = "vorkpall"
league = "EEVZA U16 neidude turniir"
level = 5
kind = "mäng"
start = 2026-11-22T15:00:00
home = "Eesti U16"
away = "Läti U16"
venue = "Kalevi spordihall"
url = "https://www.volley.ee/uudis"
added = 2026-11-20
note = "liidu uudis"

[[event]]
sport = "korvpall"
league = "Noorte jõulukarikas"
level = 4
kind = "turniir"
start = 2026-11-22
home = "Noorte jõulukarikas (U14)"
venue = "Kalevi spordihall"
url = "https://example.ee/turniir"
added = 2026-11-20
'''


def one(**over):
    """Üks kirje, kus `over` muudab või (None) eemaldab välju."""
    base = {"sport": '"jalgpall"', "league": '"Sõprusmäng"', "level": "1", "kind": '"sõprusmäng"',
            "start": "2026-12-01T18:00:00", "home": '"A"', "away": '"B"', "venue": '"Kalevi spordihall"',
            "url": '"https://klubi.ee/mang"', "added": "2026-11-22"}
    base.update(over)
    return "[[event]]\n" + "\n".join(f"{k} = {v}" for k, v in base.items() if v is not None)


class ParseTest(unittest.TestCase):
    def test_match_and_tournament(self):
        match, tour = kasitsi.parse(GOOD)
        self.assertEqual(match.start, datetime(2026, 11, 22, 15, 0, tzinfo=TALLINN))
        self.assertFalse(match.time_tbc)
        self.assertEqual((match.level, match.source, match.away), (5, "kasitsi", "Läti U16"))
        self.assertEqual(len(match.id), 12)
        # ainult kuupäev → kellaaeg täpsustamisel; turniiril külalisi pole
        self.assertTrue(tour.time_tbc)
        self.assertEqual(tour.start.date(), date(2026, 11, 22))
        self.assertEqual(tour.away, "")
        self.assertEqual(build.matchup(tour), "Noorte jõulukarikas (U14)")
        self.assertEqual(build.matchup(match), "Eesti U16 – Läti U16")

    def test_stable_id(self):
        self.assertEqual(kasitsi.parse(GOOD)[0].id, kasitsi.parse(GOOD)[0].id)

    def test_offset_time_and_result(self):
        (e,) = kasitsi.parse(one(start="2026-12-01T16:00:00Z", result='"3 - 1"'))
        self.assertEqual(e.start, datetime(2026, 12, 1, 18, 0, tzinfo=TALLINN))
        self.assertEqual(e.result, "3-1")

    def test_errors_name_entry_and_problem(self):
        cases = {
            "sport": ('"kurling"', "tundmatu ala"),
            "level": ("3", "tase 3 pole lubatud"),
            "kind": ('"pidu"', "tundmatu liik"),
            "url": ('"https://www.facebook.com/klubi/posts/1"', "sotsiaalmeedia"),
            "added": ('"eile"', "added peab olema kuupäev"),
            "start": ('"homme"', "start peab olema"),
        }
        for field, (value, message) in cases.items():
            with self.subTest(field=field):
                with self.assertRaises(ValueError) as cm:
                    kasitsi.parse(one(**{field: value}))
                self.assertIn("kirje 1 (A)", str(cm.exception))
                self.assertIn(message, str(cm.exception))

    def test_missing_and_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "puudub 'url'"):
            kasitsi.parse(one(url=None))
        with self.assertRaisesRegex(ValueError, "tundmatu väli 'linn'"):
            kasitsi.parse(one(linn='"Tallinn"'))
        with self.assertRaisesRegex(ValueError, "tundmatu jaotis"):
            kasitsi.parse('[[mang]]\nhome = "A"\n')

    def test_empty_file_is_fine(self):
        self.assertEqual(kasitsi.parse("# ainult kommentaarid\n"), [])


class RepoFileTest(unittest.TestCase):
    """Repo kasitsi.toml peab olema korras: iga kirje loetav ja saal teada ning Eestis."""

    def test_repo_file_valid_and_venues_known(self):
        events = kasitsi.load()
        venues, geo = Venues.load(), Geo(config.load())
        for e in events:
            with self.subTest(event=build.matchup(e)):
                v = venues.lookup(e.venue)
                self.assertIsNotNone(v, f"saal {e.venue!r} puudub venues.toml-ist")
                self.assertTrue(geo.is_estonian(v.city), f"{v.city} pole Eesti linn config.toml-is")


class BuildIntegrationTest(unittest.TestCase):
    def test_manual_source_never_empty_error_and_not_in_coverage(self):
        cfg = config.load()
        src = next(s for s in cfg["source"] if s["name"] == "kasitsi")
        self.assertTrue(src.get("manual"))
        self.assertEqual(build.missing_upcoming(src, [], date(2026, 11, 22)), [])  # 0 üritust pole viga
        self.assertEqual(len(build.coverage(cfg)), len(build.SPORTS))              # ei lisa ala rida ega kuku

    def test_collect_reads_file_and_normalises_venue(self):
        cfg = config.load()
        cfg = dict(cfg, source=[s for s in cfg["source"] if s["name"] == "kasitsi"])
        with mock.patch.object(kasitsi, "load", lambda path=None: kasitsi.parse(GOOD)), \
                mock.patch.object(build, "save"), mock.patch("archive.update"):
            events, report = build.collect(cfg, Venues.load(), object(), date(2026, 11, 22),
                                           archive_root=Path(tempfile.mkdtemp()))
        self.assertEqual(report[0]["status"], "ok")
        self.assertEqual(report[0]["saved"], 2)
        self.assertEqual({e.city for e in events}, {"Tallinn"})

    def test_tournament_renders_without_dash_and_with_notice_link(self):
        tmp = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/"},
               "geo": config.load()["geo"], "source": config.load()["source"]}
        events = [replace(e, city="Tallinn") for e in kasitsi.parse(GOOD)]
        build.render(events, cfg, date(2026, 11, 20), tmp)
        day = (tmp / "noored/2026-11-22/index.html").read_text(encoding="utf-8")
        self.assertIn('<span class="match">Noorte jõulukarikas (U14)</span>', day)
        self.assertNotIn("Noorte jõulukarikas (U14) –", day)
        self.assertIn("kellaaeg täpsustamisel", day)
        tour = next(e for e in events if not e.away)
        game = (tmp / f"m/{tour.id}/index.html").read_text(encoding="utf-8")
        self.assertIn('<meta property="og:title" content="Noorte jõulukarikas (U14)">', game)
        self.assertIn("Teade allika saidil ↗", game)


if __name__ == "__main__":
    unittest.main()
