import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers.model import new_event


def ev(day, hour, home, sport="jaahoki"):
    return new_event(source="t", sport=sport, league="Liiga", start=datetime(2026, 11, day, hour, 0),
                     home=home, away="Külalised", venue="Haabersti jäähall", city="Tallinn",
                     url="https://example.org/" + home)


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/"},
               "external_link": [{"sport": "korvpall", "url": "https://basket.example/"}]}
        events = [ev(22, 19, "B"), ev(22, 13, "A", sport="vorkpall"), ev(30, 12, "Kaugel")]
        build.render(events, cfg, date(2026, 11, 20), self.tmp)

    def read(self, rel):
        return (self.tmp / rel).read_text(encoding="utf-8")

    def test_pages_and_files(self):
        for rel in ["index.html", "2026-11-20/index.html", "2026-11-23/index.html",
                    "events.json", "sitemap.xml", "robots.txt", "style.css", "app.js"]:
            self.assertTrue((self.tmp / rel).exists(), rel)
        self.assertFalse((self.tmp / "2026-11-24").exists())

    def test_empty_day_links_to_next_games(self):
        html = self.read("index.html")
        self.assertIn("Täna mänge pole", html)
        self.assertIn('href="2026-11-22/"', html)

    def test_day_sorted_and_relative_links(self):
        html = self.read("2026-11-22/index.html")
        self.assertLess(html.index("A – Külalised"), html.index("B – Külalised"))
        self.assertIn('href="../style.css"', html)
        self.assertIn('rel="prev"', html)
        self.assertIn("https://basket.example/", html)
        self.assertIn('data-filter="vorkpall"', html)
        self.assertIn('aria-current="page"', html)  # päevade ribal valitud päev
        self.assertIn('class="s-jaahoki"', html)    # ala värviplokk

    def test_day_strip_marks_empty_days(self):
        html = self.read("index.html")
        self.assertIn('class="empty"', html)
        self.assertIn('<span class="wd">P</span><span class="dn">22</span>', html)

    def test_out_of_range_event_not_listed(self):
        self.assertNotIn("Kaugel", self.read("2026-11-23/index.html"))
        self.assertIn("https://example.org/sk/2026-11-21/", self.read("sitemap.xml"))


if __name__ == "__main__":
    unittest.main()
