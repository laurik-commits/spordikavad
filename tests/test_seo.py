"""SEO: mängulehe pealkiri ja JSON-LD, mängulehed kogu hooajaks, ala- ja liigalehed, sitemap, Search Console."""
import json
import re
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config
from scrapers.model import new_event

TODAY = date(2026, 11, 20)
OLD_GEO = dict(config.load()["geo"], default="tallinn")


def ev(start, home="Kalev", away="Rapla", sport="korvpall", league="Meistriliiga", venue="Kalevi spordihall",
       city="Tallinn", **kw):
    return new_event(source="t", sport=sport, league=league, start=start, home=home, away=away, venue=venue,
                     city=city, url="https://example.org/" + home, **kw)


class TitleLdTest(unittest.TestCase):
    def test_title_format_and_length(self):
        e = ev(datetime(2026, 11, 28, 19, 0))
        self.assertEqual(build.game_title(e), "Kalev – Rapla | Meistriliiga | 28. nov 19:00 | Kalevi spordihall")
        self.assertEqual(build.game_title(e, "3:1"), "Kalev – Rapla 3:1 | Meistriliiga | 28. nov 19:00 | Kalevi spordihall")
        tbc = ev(datetime(2026, 11, 28, 12, 0), time_tbc=True)
        self.assertIn("| 28. nov |", build.game_title(tbc))   # kellaajata mängul ainult kuupäev
        long = ev(datetime(2026, 11, 28, 19, 0), home="Tallinna Kalev/Tradehouse", away="Pärnu Sadam", league="Eesti-Läti Korvpalliliiga",
                  venue="Tallinna Ülikooli spordihoone")
        self.assertLessEqual(len(build.game_title(long)), build.TITLE_MAX)
        self.assertIn("Tallinna Kalev/Tradehouse – Pärnu Sadam", build.game_title(long))   # nimi jääb alati ette
        huge = ev(datetime(2026, 11, 28, 19, 0), home="X" * 40 + " nimi", away="Y" * 40, league="L")
        self.assertLessEqual(len(build.game_title(huge)), build.TITLE_MAX)

    def test_json_ld_team_game(self):
        d = json.loads(build.event_ld(ev(datetime(2026, 11, 28, 19, 0)), "https://elakaasa.ee/m/x/"))
        self.assertEqual((d["@type"], d["name"], d["startDate"]), ("SportsEvent", "Kalev – Rapla", "2026-11-28T19:00+02:00"))
        self.assertEqual((d["homeTeam"]["name"], d["awayTeam"]["name"]), ("Kalev", "Rapla"))
        self.assertEqual((d["location"]["name"], d["location"]["address"]["addressLocality"]), ("Kalevi spordihall", "Tallinn"))
        self.assertEqual(d["url"], "https://elakaasa.ee/m/x/")

    def test_json_ld_event_sport_tbc_and_no_venue(self):
        e = ev(datetime(2026, 12, 5, 12, 0), home="Rally Estonia", away="", sport="autosport", venue="", city="",
               time_tbc=True, end=date(2026, 12, 6))
        d = json.loads(build.event_ld(e, "https://x/"))
        self.assertEqual((d["startDate"], d["endDate"]), ("2026-12-05", "2026-12-06"))
        self.assertNotIn("homeTeam", d)
        self.assertNotIn("location", d)   # kohta ei välja mõelda
        only_city = json.loads(build.event_ld(ev(datetime(2026, 12, 5, 18, 0), venue="", city="Tallinn", home="Kalev"), "https://x/"))
        self.assertEqual(only_city["location"]["name"], "Tallinn")

    def test_json_ld_is_script_safe(self):
        out = build.event_ld(ev(datetime(2026, 12, 5, 18, 0), home="A</script><b>"), "https://x/")
        self.assertNotIn("</", out)

    def test_slugify(self):
        self.assertEqual(build.slugify("Eesti-Läti Korvpalliliiga"), "eesti-lati-korvpalliliiga")
        self.assertEqual(build.slugify("Meistriliiga (mehed)"), "meistriliiga-mehed")
        self.assertEqual(build.slugify("???"), "liiga")


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp())
        cls.future = ev(datetime(2027, 3, 14, 19, 0))                              # päevaakna taga
        cls.near = ev(datetime(2026, 11, 22, 18, 0), home="Tartu", away="Pärnu")
        cls.second = ev(datetime(2026, 12, 1, 18, 0), home="Rapla", away="Kalev", league="Esiliiga")
        cls.old = ev(datetime(2026, 9, 5, 18, 0), home="Vana", away="Mäng", result="80-70")   # arhiivist, ammu möödas
        cls.hidden = ev(datetime(2026, 12, 3, 18, 0), home="Madal", away="Liiga", level=3)
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/", "default_level": 1,
                        "google_site_verification": "TOKEN123"},
               "geo": OLD_GEO, "source": config.load()["source"]}
        build.render([cls.future, cls.near, cls.second, cls.hidden], cfg, TODAY, cls.out, all_games=[cls.old])

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_every_game_has_a_page(self):
        for e in (self.future, self.near, self.second, self.old, self.hidden):
            self.assertTrue((self.out / "m" / e.id / "index.html").exists(), e.home)

    def test_game_page_head(self):
        page = self.read(f"m/{self.future.id}/index.html")
        self.assertIn("<title>Kalev – Rapla | Meistriliiga | 14. märts 19:00 | Kalevi spordihall</title>", page)
        self.assertIn('"@type":"SportsEvent"', page)
        self.assertIn('<meta name="google-site-verification" content="TOKEN123">', page)
        self.assertNotIn("noindex", page)
        self.assertNotIn("Selle päeva", page)   # päevaakna taga pole päevalehte, seega ka linki pole

    def test_past_game_stays_with_note_and_league_link(self):
        page = self.read(f"m/{self.old.id}/index.html")
        self.assertIn("noindex", page)
        self.assertIn("Mäng on toimunud.", page)
        self.assertIn('href="../../korvpall/meistriliiga/"', page)
        self.assertIn("80:70", page)

    def test_sport_and_league_pages(self):
        sport = self.read("korvpall/index.html")
        self.assertIn("<title>Korvpall Eestis: eelseisvad mängud ja ajakava</title>", sport)
        self.assertIn("3 eelseisvat mängu", sport)      # future, near, second; möödunud ja peidetud ei loe
        self.assertIn('href="meistriliiga/"', sport)
        self.assertIn(f'href="../m/{self.near.id}/"', sport)
        self.assertNotIn(self.hidden.id, sport)
        league = self.read("korvpall/meistriliiga/index.html")
        self.assertIn("2 eelseisvat mängu", league)
        self.assertIn("Järgmine: Tartu – Pärnu", league)
        self.assertNotIn(self.second.id, league)         # teine liiga
        self.assertFalse((self.out / "korvpall" / "madalamad").exists())

    def test_sitemap(self):
        urls = re.findall(r"<loc>(.*?)</loc>", self.read("sitemap.xml"))
        base = "https://example.org/"
        for u in (f"{base}m/{self.future.id}/", f"{base}m/{self.near.id}/", f"{base}korvpall/",
                  f"{base}korvpall/meistriliiga/", f"{base}korvpall/esiliiga/"):
            self.assertIn(u, urls)
        self.assertNotIn(f"{base}m/{self.old.id}/", urls)      # möödunud: noindex, sitemapis pole
        self.assertNotIn(f"{base}m/{self.hidden.id}/", urls)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertNotIn("lastmod", self.read("sitemap.xml"))
        self.assertIn("Sitemap: https://example.org/sitemap.xml", self.read("robots.txt"))

    def test_internal_links_resolve(self):
        pages = [self.out / "korvpall" / "index.html", self.out / "korvpall" / "meistriliiga" / "index.html",
                 self.out / "m" / self.old.id / "index.html", self.out / "m" / self.near.id / "index.html",
                 self.out / "m" / self.future.id / "index.html"]
        for page in pages:
            for href in re.findall(r'href="([^"#?]+)"', page.read_text(encoding="utf-8")):
                if href.startswith(("http", "mailto:")):
                    continue
                target = (page.parent / href).resolve()
                with self.subTest(page=str(page.relative_to(self.out)), href=href):
                    self.assertTrue(target.exists() and (target.is_file() or (target / "index.html").exists()), target)


class ReservedSlugTest(unittest.TestCase):
    def test_sport_keys_do_not_clash_with_site_folders(self):
        from scrapers.model import LEVELS, SPORTS
        reserved = {"m", "info", *(lv["slug"] for lv in LEVELS.values())}
        self.assertFalse(reserved & set(SPORTS))


if __name__ == "__main__":
    unittest.main()
