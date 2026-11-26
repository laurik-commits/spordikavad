"""Alade register (sports.toml): kontroll, tuletatud sõnastikud ja värvide/nimede täitmine."""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

import build
from scrapers import config, sports
from scrapers.model import new_event
from datetime import datetime

OK = '''
[[group]]
key = "g:x"
name = "X"
word = "xs"

[[sport]]
key = "abc"
name = "Abc"
gen = "abc"
in = "abcs"
color = "#112233"
'''


class RegisterTest(unittest.TestCase):
    def test_repo_register_is_valid_and_complete(self):
        reg = sports.load()
        self.assertEqual(len(reg["sports"]), len(sports.SPORTS))
        for s in sports.SPORT_LIST:
            self.assertTrue(s["name"] and s["gen"] and s["in"], s["key"])
        self.assertIn("ujumine", sports.EVENT_SPORTS)
        self.assertNotIn("lauatennis", sports.EVENT_SPORTS)   # lauatennises on ka meistriliiga mängud

    def test_validation_errors(self):
        sports.parse(OK)
        for bad, why in ((OK.replace('color = "#112233"', 'color = "red"'), "värv"),
                         (OK.replace('key = "abc"', 'key = "Abc"'), "võti"),
                         (OK + '\n[[sport]]\nkey = "abc"\nname = "B"\ngen = "b"\nin = "b"\ncolor = "#000000"\n', "topelt"),
                         (OK.replace('in = "abcs"\n', ''), "puudub in"),
                         (OK.replace('color = "#112233"', 'color = "#112233"\ngroup = "g:y"'), "rühm"),
                         (OK.replace('color = "#112233"', 'color = "#112233"\nsurprise = 1'), "tundmatu väli"),
                         (OK.replace('color = "#112233"', 'color = "#112233"\nerr = "("'), "regex")):
            with self.subTest(why=why), self.assertRaises((ValueError, Exception)):
                sports.parse(bad)

    def test_fill_markers(self):
        text = "a\n/* @sports:vars */\nold\n/* @sports:end */\nb\n"
        filled = sports.fill(text)
        self.assertIn("--ujumine: #0369a1;", filled)
        self.assertNotIn("old", filled)
        self.assertEqual(sports.fill(filled), filled)   # korduv täitmine ei muuda
        with self.assertRaises(ValueError):
            sports.fill("/* @sports:nope */\n/* @sports:end */")

    def test_source_files_have_all_markers(self):
        root = Path(__file__).parent.parent / "site"
        css = (root / "style.css").read_text(encoding="utf-8")
        js = (root / "kalender.js").read_text(encoding="utf-8")
        for name in ("vars", "border", "fill"):
            self.assertIn(f"/* @sports:{name} */", css)
        self.assertIn("/* @sports:js */", js)
        self.assertNotIn("--ujumine:", css)   # värvid pole lähtefailis, need tulevad registrist

    def test_built_assets_have_every_sport(self):
        out = Path(tempfile.mkdtemp())
        ev = new_event(source="t", sport="ujumine", league="L", start=datetime(2026, 11, 22, 19, 0), home="X",
                       away="", venue="Aura Veekeskus", city="Tartu", url="https://example.org/")
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/", "default_level": 1},
               "geo": dict(config.load()["geo"], default="tallinn"), "source": config.load()["source"]}
        build.render([ev], cfg, date(2026, 11, 20), out)
        css = (out / "style.css").read_text(encoding="utf-8")
        js = (out / "kalender.js").read_text(encoding="utf-8")
        for k, name in sports.SPORTS.items():
            self.assertIn(f"--{k}:", css)
            self.assertIn(f".s-{k} {{", css)
            self.assertRegex(js, rf"\b{k}: \"{re.escape(name)}\"")
        self.assertIn("Saali­jalgpall", js)


if __name__ == "__main__":
    unittest.main()
