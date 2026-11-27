"""Praktikumi lisaleht /praktikum/: tehakse ainult siis, kui materjalide kaustas on faile; ei ole sitemapis ega indekseeritav."""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

import build
import praktikum
from scrapers import config

TODAY = date(2026, 11, 20)


def render_with(src: Path) -> Path:
    out = Path(tempfile.mkdtemp())
    cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/", "default_level": 1},
           "geo": dict(config.load()["geo"], default="tallinn"), "source": config.load()["source"]}
    build.render([], cfg, TODAY, out, praktikum_dir=src)
    return out


class PraktikumTest(unittest.TestCase):
    def setUp(self):
        self.src = Path(tempfile.mkdtemp()) / "praktikum"
        (self.src / "materjalid").mkdir(parents=True)

    def test_no_files_no_page(self):
        (self.src / "materjalid" / ".gitkeep").write_text("")
        out = render_with(self.src)
        self.assertFalse((out / "praktikum").exists())

    def test_page_lists_files_and_copies_them(self):
        m = self.src / "materjalid"
        (m / "slaidid 10.pdf").write_bytes(b"x" * 2048)
        (m / "slaidid 2.pdf").write_bytes(b"y" * 10)
        (m / "1. praktikum").mkdir()
        (m / "1. praktikum" / "ülesanne õ.docx").write_bytes(b"z" * 3_000_000)
        (m / ".gitkeep").write_text("")
        (self.src / "praktikum.toml").write_text(
            'title = "ChatGPT Edu praktikum"\nintro = "Materjalid <b>tudengitele</b>."\n\n'
            '[[fail]]\nnimi = "slaidid 2.pdf"\nkirjeldus = "Sissejuhatus"\n\n'
            '[[fail]]\nnimi = "1. praktikum/ülesanne õ.docx"\nkirjeldus = "Ülesanne"\n', encoding="utf-8")
        out = render_with(self.src)
        page = (out / "praktikum" / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>ChatGPT Edu praktikum</title>", page)
        self.assertIn('<meta name="robots" content="noindex, nofollow">', page)
        self.assertNotIn("<b>tudengitele</b>", page)               # tekst on escape'itud
        self.assertIn("&lt;b&gt;tudengitele&lt;/b&gt;", page)
        self.assertLess(page.index("slaidid 2.pdf"), page.index("slaidid 10.pdf"))   # loomulik järjekord
        self.assertIn('href="materjalid/slaidid%202.pdf"', page)
        self.assertIn('href="materjalid/1.%20praktikum/%C3%BClesanne%20%C3%B5.docx"', page)
        self.assertIn("(2 KB)", page)
        self.assertIn("(2.9 MB)", page)
        self.assertIn("Sissejuhatus", page)
        self.assertIn("<h2>1. praktikum</h2>", page)
        self.assertNotIn(".gitkeep", page)
        self.assertEqual((out / "praktikum" / "materjalid" / "slaidid 2.pdf").read_bytes(), b"y" * 10)
        self.assertTrue((out / "praktikum" / "materjalid" / "1. praktikum" / "ülesanne õ.docx").exists())
        self.assertFalse((out / "praktikum" / "materjalid" / ".gitkeep").exists())

    def test_not_in_sitemap_not_tracked_not_robots_blocked(self):
        (self.src / "materjalid" / "a.pdf").write_bytes(b"a")
        out = render_with(self.src)
        self.assertNotIn("praktikum", (out / "sitemap.xml").read_text(encoding="utf-8"))
        page = (out / "praktikum" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("cloudflareinsights", page)             # statistika koodi lehel pole
        # robots.txt ei keela: muidu ei näeks otsingumootor noindex-i
        self.assertNotIn("praktikum", (out / "robots.txt").read_text(encoding="utf-8"))

    def test_internal_links_resolve(self):
        (self.src / "materjalid" / "fail üks.pdf").write_bytes(b"a")
        out = render_with(self.src)
        page = out / "praktikum" / "index.html"
        from urllib.parse import unquote
        for href in re.findall(r'href="([^"#?]+)"', page.read_text(encoding="utf-8")):
            if href.startswith(("http", "mailto:")):
                continue
            self.assertTrue((page.parent / unquote(href)).exists(), href)

    def test_slug_is_reserved_against_sport_keys(self):
        from scrapers.model import SPORTS
        self.assertNotIn(praktikum.SLUG, SPORTS)

    def test_repo_folder_has_readme_and_materials_folder(self):
        root = Path(__file__).parent.parent / "site" / "praktikum"
        self.assertTrue((root / "README.md").exists())
        self.assertTrue((root / "materjalid").is_dir())


if __name__ == "__main__":
    unittest.main()
