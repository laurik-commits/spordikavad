"""Iga ala on kõikjal olemas: mudel, lauseosad, allikad, värvid, kalender.js ja rühmad."""
import re
import unittest
from pathlib import Path

import build
from scrapers.model import EVENT_SPORTS, SPORTS

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "site" / "style.css").read_text(encoding="utf-8")
JS = (ROOT / "site" / "kalender.js").read_text(encoding="utf-8")


class SportsConsistencyTest(unittest.TestCase):
    def test_every_sport_everywhere(self):
        js_sports = set(re.findall(r"(\w+):\s*\"[^\"]+\"", JS.split("var SPORTS = {")[1].split("};")[0]))
        for s in SPORTS:
            with self.subTest(sport=s):
                self.assertIn(s, build.SPORT_IN)
                self.assertIn(s, build.SPORT_GEN)
                self.assertIn(s, build.SOURCE_SITES)
                self.assertIn(f".s-{s} {{", CSS)
                self.assertIn(f"--{s}:", CSS)
                self.assertIn(s, js_sports)

    def test_groups(self):
        seen = set()
        for g in build.SPORT_GROUPS:
            self.assertTrue(g["key"].startswith("g:"))
            for s in g["sports"]:
                self.assertIn(s, SPORTS)
                self.assertNotIn(s, seen, f"{s} on kahes rühmas")
                seen.add(s)
        kunst = next(g for g in build.SPORT_GROUPS if g["key"] == "g:kunst")
        self.assertEqual((kunst["name"], kunst["sports"]), ("Kunstilised alad", ["voimlemine", "tantsusport", "fitness"]))
        self.assertTrue({"voimlemine", "tantsusport", "fitness"} <= EVENT_SPORTS)
        vesi = next(g for g in build.SPORT_GROUPS if g["key"] == "g:vesi")
        self.assertEqual((vesi["name"], vesi["sports"]), ("Veealad", ["ujumine", "soudmine", "kanuu", "purjetamine"]))
        self.assertTrue(set(vesi["sports"]) <= EVENT_SPORTS)

    def test_manual_sports_are_in_coverage(self):
        # käsitsi kaetud alad (otsinguagent) on „Meist“ tabelis ja menüüs
        cov = {row["key"]: row for row in build.coverage({"source": []})}
        for s in ("voimlemine", "tantsusport", "fitness", "lauatennis", "soudmine", "kanuu", "purjetamine"):
            self.assertTrue(cov[s]["top"], s)


if __name__ == "__main__":
    unittest.main()
