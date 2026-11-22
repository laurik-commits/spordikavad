import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import build
from scrapers import config
from scrapers.geo import Geo
from scrapers.model import new_event
from scrapers.venues import Venues


def ev(day, hour, home, sport="jaahoki", venue="Haabersti jäähall", city="Tallinn", level=1):
    return new_event(source="t", sport=sport, league="Liiga", start=datetime(2026, 11, day, hour, 0),
                     home=home, away="Külalised", venue=venue, city=city,
                     url="https://example.org/" + home, level=level)


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/"},
               "geo": config.load()["geo"], "source": config.load()["source"],
               "external_link": [{"sport": "korvpall", "url": "https://basket.example/",
                                  "note": "Korvpalli andmeid ei koguta.", "link_text": "Ajakava"}],
               "sport_note": [{"sport": "jaahoki", "note": "Eesti hokiliigasid pole.", "url": "https://hoki.example/"}]}
        events = [ev(22, 19, "B"), ev(22, 13, "A", sport="vorkpall"), ev(30, 12, "Kaugel"),
                  ev(21, 18, "Tartlased", sport="kasipall", venue="Tartu Ülikooli spordihoone", city="Tartu"),
                  ev(21, 17, "Viimsilased", sport="kasipall", venue="Viimsi Kool", city="Viimsi"),
                  ev(21, 19, "Esiliigalased", sport="jalgpall", venue="Wismari jalgpallistaadion", level=2),
                  ev(21, 15, "Madalamlased", sport="jalgpall", venue="Männiku kunstmuruväljak", level=3),
                  ev(21, 12, "Noorukid", sport="saalijalgpall", venue="Kalevi spordihall", level=4),
                  ev(21, 20, "Koondislased", sport="jalgpall", venue="Wismari jalgpallistaadion", level=5)]
        build.render(events, cfg, date(2026, 11, 20), self.tmp)

    def read(self, rel):
        return (self.tmp / rel).read_text(encoding="utf-8")

    def test_pages_and_files(self):
        for rel in ["index.html", "2026-11-20/index.html", "2026-11-23/index.html",
                    "eesti/index.html", "eesti/2026-11-21/index.html", "tartu/2026-11-21/index.html",
                    "harjumaa/2026-11-21/index.html",
                    "events.json", "sitemap.xml", "robots.txt", "style.css", "app.js"]:
            self.assertTrue((self.tmp / rel).exists(), rel)
        self.assertFalse((self.tmp / "2026-11-24").exists())
        self.assertFalse((self.tmp / "parnu").exists())  # Pärnus mänge pole → valikus pole

    def test_empty_day_links_to_next_games(self):
        html = self.read("index.html")
        self.assertIn("Täna Tallinnas kõrgliigade mänge pole", html)
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
        self.assertIn('Korvpalli andmeid ei koguta. <a href="https://basket.example/"', html)
        self.assertIn('data-filter="korvpall" data-ext="1"', html)  # korvpall on nupp, mitte link

    def test_all_sports_always_listed_with_reason_when_empty(self):
        html = self.read("2026-11-22/index.html")
        for s in ("jalgpall", "jaahoki", "vorkpall", "kasipall", "saalihoki", "saalijalgpall"):
            self.assertIn(f'data-filter="{s}"', html)
        self.assertIn('data-filter="saalihoki" aria-pressed="false" class="nogames" data-none="1"', html)
        self.assertIn("Tallinnas pole järgmise 2 nädala jooksul saalihoki kõrgliigade mänge.", html)
        self.assertIn("Jalgpalli hooaeg algab märtsis.", html)          # talvel hooajaväline
        self.assertNotIn('data-filter="vorkpall" aria-pressed="false" class="nogames"', html)
        # esiliigades jäähokit pole üldse → nuppu pole
        self.assertNotIn('data-filter="jaahoki"', self.read("esiliigad/2026-11-21/index.html"))

    def test_sport_note_only_where_sport_is_listed(self):
        self.assertIn('data-note="jaahoki">Eesti hokiliigasid pole.', self.read("2026-11-22/index.html"))
        self.assertIn("Eesti hokiliigasid pole", self.read("tartu/2026-11-21/index.html"))  # hoki nupp on alati
        self.assertNotIn("Eesti hokiliigasid pole", self.read("esiliigad/2026-11-21/index.html"))  # esiliigas hokit pole

    def test_regions_split_and_city_shown_only_when_needed(self):
        tallinn = self.read("2026-11-21/index.html")
        self.assertNotIn("Tartlased", tallinn)
        tartu = self.read("tartu/2026-11-21/index.html")
        self.assertIn("Tartlased", tartu)
        self.assertNotIn("spordihoone, Tartu</span>", tartu)   # linna vaates linna ei korrata (jagamistekstis on)
        self.assertIn('href="../../style.css"', tartu)
        self.assertIn("Spordimängud Tartus", tartu)
        harju = self.read("harjumaa/2026-11-21/index.html")
        self.assertIn("Viimsilased", harju)
        self.assertIn("Viimsi Kool, Viimsi", harju)
        self.assertIn("Harjumaa (v.a Tallinn)", harju)
        eesti = self.read("eesti/2026-11-21/index.html")
        self.assertIn("Tartlased", eesti)
        self.assertIn("Viimsilased", eesti)
        self.assertIn("Spordimängud Eestis", eesti)

    def test_city_picker_links_keep_the_day(self):
        tartu = self.read("tartu/2026-11-21/index.html")
        self.assertIn('href="../../2026-11-21/" data-region="tallinn"', tartu)
        self.assertIn('href="../../eesti/2026-11-21/" data-region="eesti"', tartu)
        root = self.read("index.html")
        self.assertIn('data-index="1"', root)
        self.assertIn('href="tartu/2026-11-20/" data-region="tartu"', root)

    def test_esiliigad_separate_calendar(self):
        top = self.read("2026-11-21/index.html")
        self.assertNotIn("Esiliigalased", top)
        low = self.read("esiliigad/2026-11-21/index.html")
        self.assertIn("Esiliigalased", low)
        self.assertNotIn("Tartlased", low)                       # kõrgliiga mäng ei satu esiliigadesse
        self.assertIn("Esiliigade mängud Tallinnas", low)
        self.assertIn('href="../../style.css"', low)
        self.assertIn('href="../../2026-11-21/" data-level="1"', low)  # tagasi kõrgliigadesse, sama päev
        self.assertIn('href="../../esiliigad/tartu/2026-11-21/" data-region="tartu"', low)
        self.assertTrue((self.tmp / "esiliigad/tartu/2026-11-21/index.html").exists())
        tartu_low = self.read("esiliigad/tartu/2026-11-21/index.html")
        self.assertIn('href="../../../style.css"', tartu_low)
        self.assertIn("Sel päeval Tartus esiliigade mänge pole", tartu_low)

    def test_madalamad_separate_calendar(self):
        low = self.read("madalamad/2026-11-21/index.html")
        self.assertIn("Madalamlased", low)
        self.assertNotIn("Esiliigalased", low)                   # tasemed ei sega üksteist
        self.assertNotIn("Madalamlased", self.read("esiliigad/2026-11-21/index.html"))
        self.assertNotIn("Madalamlased", self.read("2026-11-21/index.html"))
        self.assertIn("Madalamate liigade mängud Tallinnas", low)
        self.assertIn('href="../../2026-11-21/" data-level="1"', low)
        self.assertIn('href="../../esiliigad/2026-11-21/" data-level="2"', low)
        self.assertIn("Madalamate liigade spordimängud", self.read("madalamad/index.html"))  # sissejuhatus avalehel
        self.assertIn("Sel päeval Tartus madalamate liigade mänge pole",
                      self.read("madalamad/tartu/2026-11-21/index.html"))
        # madalamates liigades on ainult jalgpall → teisi alanuppe pole
        self.assertIn('data-filter="jalgpall"', low)
        self.assertNotIn('data-filter="jaahoki"', low)

    def test_noored_separate_calendar(self):
        youth = self.read("noored/2026-11-21/index.html")
        self.assertIn("Noorukid", youth)
        for other in ("Madalamlased", "Esiliigalased", "Tartlased"):
            self.assertNotIn(other, youth)
        for rel in ("2026-11-21", "esiliigad/2026-11-21", "madalamad/2026-11-21"):
            self.assertNotIn("Noorukid", self.read(f"{rel}/index.html"))
        self.assertIn("Noorte mängud Tallinnas", youth)
        self.assertNotIn('data-level="3"', youth)  # madalamad liigad on ajutiselt valikust peidus
        self.assertIn('data-level="4" aria-current="true"', youth)
        self.assertIn("Sel päeval Tartus noorteliigade mänge pole", self.read("noored/tartu/2026-11-21/index.html"))
        self.assertTrue((self.tmp / "noored/index.html").exists())

    def test_koondised_separate_calendar(self):
        national = self.read("koondised/2026-11-21/index.html")
        self.assertIn("Koondislased", national)
        for other in ("Noorukid", "Madalamlased", "Esiliigalased"):
            self.assertNotIn(other, national)
        for rel in ("2026-11-21", "esiliigad/2026-11-21", "madalamad/2026-11-21", "noored/2026-11-21"):
            self.assertNotIn("Koondislased", self.read(f"{rel}/index.html"))
        self.assertIn("Koondiste mängud Tallinnas", national)
        self.assertIn('data-level="5" aria-current="true"', national)
        self.assertIn("Sel päeval Tartus koondiste mänge pole", self.read("koondised/tartu/2026-11-21/index.html"))

    def test_all_levels_view_has_everything_except_hidden_lower_leagues(self):
        everything = self.read("koik/2026-11-21/index.html")
        for team in ("Esiliigalased", "Noorukid", "Koondislased"):
            self.assertIn(team, everything)
        self.assertIn("Tartlased", self.read("koik/tartu/2026-11-21/index.html"))   # piirkonnad töötavad ka siin
        self.assertNotIn("Madalamlased", everything)           # madalamad liigad pole vaatamas käimiseks
        self.assertIn("Kõik spordimängud Tallinnas", everything)
        self.assertIn('data-level="0" aria-current="true"', everything)
        self.assertIn('<meta name="robots" content="noindex">', everything)    # kordab teisi lehti
        self.assertTrue((self.tmp / "koik/index.html").exists())
        self.assertTrue((self.tmp / "koik/tartu/2026-11-21/index.html").exists())
        # kõrgliigade valik näitab nüüd valikus "Kõik liigad" esimesena ja sitemapis seda ei ole
        menu = self.read("2026-11-21/index.html")
        self.assertLess(menu.index("<span>Kõik liigad</span>"), menu.index("<span>Kõrgliigad</span>"))
        self.assertNotIn("/koik/", self.read("sitemap.xml"))

    def test_share_button_and_game_page_with_preview(self):
        import re
        day = self.read("2026-11-22/index.html")
        self.assertIn('<meta property="og:image" content="https://example.org/sk/og.png">', day)
        self.assertTrue((self.tmp / "og.png").exists())
        m = re.search(r'class="share" data-url="https://example.org/sk/m/([0-9a-f]{12})/" '
                      r'data-title="A – Külalised" data-text="([^"]+)"', day)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "A – Külalised: pühapäev, 22. november kell 13:00, Haabersti jäähall, Tallinn")
        game = self.read(f"m/{m.group(1)}/index.html")
        self.assertIn('<meta property="og:title" content="A – Külalised">', game)
        self.assertIn('<meta property="og:description" content="pühapäev, 22. november kell 13:00, '
                      'Haabersti jäähall, Tallinn · Võrkpall, Liiga">', game)
        self.assertIn(f'<link rel="canonical" href="https://example.org/sk/m/{m.group(1)}/">', game)
        self.assertIn('href="https://example.org/A"', game)                 # allika mängu leht
        self.assertIn('href="../../eesti/2026-11-22/"', game)               # sama päeva kõik mängud
        self.assertNotIn("noindex", game)
        # igal aknas oleval mängul on oma leht (ka teiste tasemete omadel); 30.11 mäng on aknast väljas
        self.assertEqual(len(list((self.tmp / "m").iterdir())), 8)
        self.assertIn("/m/", self.read("404.html"))                         # vana mängu link → tänased mängud

    def test_year_round_sources_do_not_hide_offseason_note(self):
        # koondised on terve aasta "hooajas", aga jalgpalli liigahooaeg algab ikka märtsis
        self.assertIn("Jalgpalli hooaeg algab märtsis.", self.read("2026-11-22/index.html"))

    def test_coverage_national_column(self):
        rows = {r["key"]: r for r in build.coverage(config.load())}
        self.assertIn("Meeste koondis", rows["jalgpall"]["national"])
        self.assertIn("Saalijalgpalli koondis", rows["saalijalgpall"]["national"])
        self.assertNotIn("Meeste koondis", rows["jalgpall"]["top"])
        self.assertEqual(rows["korvpall"]["national"], [])

    def test_coverage_youth_column(self):
        rows = {r["key"]: r for r in build.coverage(config.load())}
        self.assertIn("U18 saalijalgpalli eliitliiga", rows["saalijalgpall"]["youth"])
        self.assertIn("U16 esiliiga", rows["jalgpall"]["youth"])
        self.assertNotIn("U16 esiliiga", rows["jalgpall"]["minor"])
        self.assertEqual(rows["korvpall"]["youth"], [])

    def test_coverage_has_minor_column(self):
        rows = {r["key"]: r for r in build.coverage(config.load())}
        self.assertIn("II liiga", rows["jalgpall"]["minor"])
        self.assertNotIn("II liiga", rows["jalgpall"]["low"])
        self.assertEqual(rows["korvpall"]["minor"], [])

    def test_day_strip_marks_empty_days(self):
        html = self.read("index.html")
        self.assertIn('class="empty"', html)
        self.assertIn('<span class="wd">P</span><span class="dn">22</span>', html)
        # päeva alad filtri jaoks (22.11: jäähoki ja võrkpall, 21.11 Tallinna kõrgliigades tühi)
        self.assertIn('href="2026-11-22/" class="" data-sports="jaahoki vorkpall"', html)
        self.assertIn('href="2026-11-21/" class="empty" data-sports=""', html)

    def test_out_of_range_event_not_listed(self):
        self.assertNotIn("Kaugel", self.read("2026-11-23/index.html"))
        sitemap = self.read("sitemap.xml")
        self.assertIn("https://example.org/sk/2026-11-22/", sitemap)
        self.assertNotIn("https://example.org/sk/2026-11-21/", sitemap)   # tühi päev sitemap'i ei lähe
        self.assertNotIn("https://example.org/sk/2026-11-20/", sitemap)   # tänane = avaleht
        self.assertIn("https://example.org/sk/tartu/2026-11-21/", sitemap)
        self.assertIn("https://example.org/sk/info/", sitemap)

    def test_canonical_today_points_to_index(self):
        self.assertIn('<link rel="canonical" href="https://example.org/sk/">', self.read("2026-11-20/index.html"))
        self.assertIn('<link rel="canonical" href="https://example.org/sk/2026-11-22/">',
                      self.read("2026-11-22/index.html"))

    def test_404_redirects_old_dates_within_site(self):
        page = self.read("404.html")
        self.assertIn('href="/sk/style.css"', page)
        self.assertIn('indexOf("/sk/")', page)
        self.assertIn("noindex", page)

    def test_old_days_are_kept_for_two_weeks(self):
        self.assertTrue((self.tmp / "2026-11-06" / "index.html").exists())   # 14 päeva tagasi
        self.assertFalse((self.tmp / "2026-11-05").exists())
        self.assertIn('rel="prev"', self.read("2026-11-20/index.html"))  # tänasel on nüüd eelmine päev
        self.assertIn('<li><a href="2026-11-19/" class="empty past"', self.read("index.html"))  # ribal hallilt

    def test_old_day_page_shows_result_and_stats_link(self):
        events = [new_event(source="t", sport="jaahoki", league="Liiga", start=datetime(2026, 11, 14, 18, 0),
                            home="Kodu", away="Võõras", venue="Haabersti jäähall", city="Tallinn",
                            url="https://example.org/mang", result="3-1"),
                  new_event(source="t", sport="jaahoki", league="Liiga", start=datetime(2026, 11, 14, 20, 0),
                            home="Teine", away="Kolmas", venue="Haabersti jäähall", city="Tallinn",
                            url="https://example.org/mang2")]
        out = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/"}, "geo": config.load()["geo"],
               "source": config.load()["source"]}
        build.render(events, cfg, date(2026, 11, 20), out)
        page = (out / "2026-11-14" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', page)
        self.assertIn("Möödunud päev", page)
        self.assertIn('<b class="score" title="Tulemus">3:1</b>', page)
        self.assertIn("Statistika ↗", page)   # tulemusega mäng
        self.assertIn("Seis ↗", page)          # tulemuseta mäng: viide allika lehele
        self.assertIn('href="https://example.org/mang"', page)
        self.assertNotIn("noindex", (out / "2026-11-21" / "index.html").read_text(encoding="utf-8"))
        self.assertIn('<main class="wrap pastday">', page)   # möödunud päeva mänguread on hallid
        self.assertNotIn("pastday", (out / "2026-11-21" / "index.html").read_text(encoding="utf-8"))
        # vanu päevi ei pakuta otsingumootoritele, valikute numbrid loevad ainult tulevasi mänge
        self.assertNotIn("2026-11-14", (out / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertNotIn("Statistika", (out / "index.html").read_text(encoding="utf-8"))
        self.assertIn('<span class="n">–</span>', (out / "index.html").read_text(encoding="utf-8"))

    def test_info_page_lists_coverage_and_update_time(self):
        info = self.read("info/index.html")
        self.assertIn("Mis siin on?", info)
        self.assertIn("Korvpall", info)
        self.assertIn("Viimati uuendatud", info)
        root = self.read("index.html")
        self.assertIn('href="info/"', root)
        self.assertIn('class="intro"', root)
        self.assertNotIn('class="intro"', self.read("2026-11-22/index.html"))  # sissejuhatus ainult avalehel
        self.assertIn('data-built="2026-11-20"', root)


class GeoTest(unittest.TestCase):
    def test_every_venue_city_is_classified(self):
        geo = Geo(config.load())
        unclassified = {v.city for v in Venues.load().venues if not geo.is_known(v.city)}
        self.assertEqual(unclassified, set(), "lisa config.toml [geo] alla")

    def test_regions(self):
        geo = Geo(config.load())
        self.assertEqual(geo.region_of("Tallinn").slug, "tallinn")
        self.assertEqual(geo.region_of("Rae vald").slug, "harjumaa")
        self.assertEqual(geo.region_of("Elva").name, "Tartumaa (v.a Tartu)")
        self.assertEqual(geo.region_of("Raplamaa") , None)
        self.assertIsNone(geo.region_of("Riia"))
        self.assertFalse(geo.is_estonian("Riia"))


if __name__ == "__main__":
    unittest.main()
