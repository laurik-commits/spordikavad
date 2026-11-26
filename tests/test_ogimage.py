"""OG-pildid: tekstipõhine 1200×630 PNG eelseisvatele mängudele, ülejäänutel üldine og.png."""
import io
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import build
import ogimage
from scrapers import config
from scrapers.model import new_event

TODAY = date(2026, 11, 20)


def png_size(data: bytes):
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.size, img.format


class OgImageTest(unittest.TestCase):
    def test_renders_1200x630_png_with_estonian_text(self):
        data = ogimage.render("Tartu Ülikool Maks & Moorits – Pärnu Sadam", "laupäev, 5. detsember kell 18:00",
                              "Tartu Ülikooli spordihoone, Tartu", "Eesti-Läti Korvpalliliiga", "Korvpall", "#6b7280")
        self.assertEqual(png_size(data), ((1200, 630), "PNG"))
        self.assertLess(len(data), 80_000)

    def test_very_long_and_empty_fields_do_not_fail(self):
        long = ogimage.render("X" * 300, "a" * 200, "b" * 200, "c" * 200, "Võitlusspordid", "#3f3f46")
        self.assertEqual(png_size(long)[0], (1200, 630))
        bare = ogimage.render("Kalev", "5. dets", "", "", "Tennis", "#4d7c0f")
        self.assertEqual(png_size(bare)[0], (1200, 630))

    def test_missing_font_gives_none_not_error(self):
        with mock.patch.object(ogimage, "FONTS", Path(tempfile.mkdtemp())):
            self.assertIsNone(ogimage.render("A – B", "x", "y", "z", "Korvpall", "#6b7280"))

    def test_font_files_ship_with_repo(self):
        for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
            self.assertTrue((ogimage.FONTS / name).exists(), name)


class BuildOgTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp())
        cls.up = new_event(source="t", sport="korvpall", league="Meistriliiga", start=datetime(2026, 12, 5, 18, 0),
                           home="Kalev", away="Rapla", venue="Kalevi spordihall", city="Tallinn", url="https://example.org/")
        cls.old = new_event(source="t", sport="korvpall", league="Meistriliiga", start=datetime(2026, 9, 5, 18, 0),
                            home="Vana", away="Mäng", venue="Kalevi spordihall", city="Tallinn", url="https://example.org/x")
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/", "default_level": 1},
               "geo": dict(config.load()["geo"], default="tallinn"), "source": config.load()["source"]}
        build.render([cls.up], cfg, TODAY, cls.out, all_games=[cls.old])

    def test_upcoming_game_has_own_image_and_meta(self):
        png = (self.out / "m" / self.up.id / "og.png").read_bytes()
        self.assertEqual(png_size(png)[0], (1200, 630))
        page = (self.out / "m" / self.up.id / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'<meta property="og:image" content="https://example.org/m/{self.up.id}/og.png">', page)

    def test_past_game_uses_generic_image(self):
        self.assertFalse((self.out / "m" / self.old.id / "og.png").exists())
        page = (self.out / "m" / self.old.id / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta property="og:image" content="https://example.org/og.png">', page)

    def test_without_pillow_font_build_still_works_with_generic_image(self):
        out = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/", "default_level": 1},
               "geo": dict(config.load()["geo"], default="tallinn"), "source": config.load()["source"]}
        with mock.patch.object(ogimage, "FONTS", Path(tempfile.mkdtemp())):
            build.render([self.up], cfg, TODAY, out)
        self.assertFalse((out / "m" / self.up.id / "og.png").exists())
        page = (out / "m" / self.up.id / "index.html").read_text(encoding="utf-8")
        self.assertIn('content="https://example.org/og.png"', page)


if __name__ == "__main__":
    unittest.main()
