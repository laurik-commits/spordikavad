import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import build

from scrapers import config
from scrapers.geo import Geo
from scrapers.model import new_event
from scrapers.venues import Venues

# Need testid kasutavad vana paigutust (juurkaustas Tallinn + kõrgliigad), et kontrollida üldist loogikat.
# Päris seadistust (Kogu Eesti + kõik liigad juurkaustas) kontrollib ProductionLayoutTest.
OLD_GEO = dict(config.load()["geo"], default="tallinn")


def ev(day, hour, home, sport="jaahoki", venue="Haabersti jäähall", city="Tallinn", level=1):
    return new_event(source="t", sport=sport, league="Liiga", start=datetime(2026, 11, day, hour, 0),
                     home=home, away="Külalised", venue=venue, city=city,
                     url="https://example.org/" + home, level=level)


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/", "default_level": 1},
               "geo": OLD_GEO, "source": config.load()["source"],
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
        self.assertIn("Täna ei ole Tallinnas ühtegi kõrgliigamängu.", html)
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
        self.assertIn("Järgmise kahe nädala jooksul ei ole Tallinnas saalihoki kõrgliigamänge.", html)
        self.assertIn("Jalgpalli hooaeg algab märtsis.", html)          # talvel hooajaväline
        self.assertNotIn('data-filter="vorkpall" aria-pressed="false" class="nogames"', html)
        # esiliigades jäähokit pole üldse → nuppu pole
        self.assertNotIn('data-filter="jaahoki"', self.read("esiliigad/2026-11-21/index.html"))

    def test_sport_picker_is_header_menu_with_counts(self):
        html = self.read("2026-11-22/index.html")
        header = html[html.index('<header'):html.index('</header>')]
        self.assertIn('<details class="sport pick-menu">', header)
        self.assertIn('<span class="cur">Kõik alad</span>', header)
        # hall (mängudeta) ala: arvu asemel kriips
        i = header.index('data-filter="saalihoki"')
        self.assertIn('<span class="n">–</span>', header[i:i + 400])

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
        self.assertIn("Sel päeval ei ole Tartus ühtegi esiliigamängu.", tartu_low)

    def test_madalamad_separate_calendar(self):
        low = self.read("madalamad/2026-11-21/index.html")
        self.assertIn("Madalamlased", low)
        self.assertNotIn("Esiliigalased", low)                   # tasemed ei sega üksteist
        self.assertNotIn("Madalamlased", self.read("esiliigad/2026-11-21/index.html"))
        self.assertNotIn("Madalamlased", self.read("2026-11-21/index.html"))
        self.assertIn("Madalamate liigade mängud Tallinnas", low)
        self.assertIn('href="../../2026-11-21/" data-level="1"', low)
        self.assertIn('href="../../esiliigad/2026-11-21/" data-level="2"', low)
        self.assertIn("Madalamate liigade mängud, mida saab kohapeal vaatama minna.", self.read("madalamad/index.html"))  # sissejuhatus avalehel
        self.assertIn("Sel päeval ei ole Tartus ühtegi madalama liiga mängu.",
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
        self.assertIn("Sel päeval ei ole Tartus ühtegi noortemängu.", self.read("noored/tartu/2026-11-21/index.html"))
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
        self.assertIn("Sel päeval ei ole Tartus ühtegi koondisemängu.", self.read("koondised/tartu/2026-11-21/index.html"))

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
        self.assertEqual(rows["korvpall"]["top"].count("FIBA Europe Cup"), 1)   # kaks allikat, üks rida

    def test_coverage_hockey_sources(self):
        rows = {r["key"]: r for r in build.coverage(config.load())}
        self.assertEqual(rows["jaahoki"]["top"], ["Optibet Hokiliiga", "Unibet Hokiliiga", "Naiste hokiliiga"])
        self.assertEqual(rows["jaahoki"]["youth"], ["U19 noorteliiga", "U16 noorteliiga"])
        self.assertEqual([name for name, _ in rows["jaahoki"]["source"]],
                         ["Läti Jäähokiliit (Optibet Hokiliiga)", "HC Vipers (Unibet Hokiliiga)",
                          "HC Everest (Unibet Hokiliiga, naiste hokiliiga, noored)"])
        self.assertTrue(all(url.startswith("https://") for r in rows.values() for _, url in r["source"]))

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
        self.assertIn('var base = "/sk/"', page)
        self.assertIn('base + "eesti/"', page)   # vanad Kogu Eesti / kõik liigad aadressid suunatakse ümber
        self.assertIn('base + "koik/"', page)
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
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/", "default_level": 1}, "geo": OLD_GEO,
               "source": config.load()["source"]}
        build.render(events, cfg, date(2026, 11, 20), out)
        page = (out / "2026-11-14" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', page)
        self.assertIn("See päev on möödas", page)
        self.assertIn('<b class="score" title="Tulemus">3:1</b>', page)
        self.assertIn("Statistika ↗", page)   # tulemusega mäng
        self.assertIn("Tulemus ↗", page)       # tulemuseta mäng: viide allika lehele
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
        self.assertNotIn("Madalamad liigad", info)   # peidetud tase pole info tabelis
        self.assertIn('<a href="https://hcvipers.ee/?page=games&amp;lang=et" rel="noopener">HC Vipers (Unibet Hokiliiga)</a>', info)
        root = self.read("index.html")
        self.assertIn('href="info/"', root)
        self.assertIn('class="intro"', root)
        self.assertNotIn('class="intro"', self.read("2026-11-22/index.html"))  # sissejuhatus ainult avalehel
        self.assertIn('data-built="2026-11-20"', root)


class AnalyticsTest(unittest.TestCase):
    BEACON = "static.cloudflareinsights.com/beacon.min.js"

    def render(self, **site):
        tmp = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 2, "base_url": "https://example.org/", "default_level": 1, **site},
               "geo": OLD_GEO, "source": config.load()["source"]}
        events = [ev(21, 19, "A")]
        build.render(events, cfg, date(2026, 11, 20), tmp)
        pages = ["index.html", "2026-11-21/index.html", "info/index.html", "404.html",
                 f"m/{events[0].id}/index.html"]
        return {p: (tmp / p).read_text(encoding="utf-8") for p in pages}

    def test_beacon_on_every_page_when_enabled(self):
        pages = self.render(analytics_enabled=True, analytics_token="abc123")
        for name, html in pages.items():
            with self.subTest(page=name):
                self.assertIn(self.BEACON, html)
                self.assertIn('data-cf-beacon=\'{"token": "abc123"}\'', html)
        self.assertIn("ei kasuta küpsiseid", pages["info/index.html"])

    def test_no_beacon_by_default(self):
        for name, html in self.render().items():
            with self.subTest(page=name):
                self.assertNotIn(self.BEACON, html)
                self.assertNotIn("Privaatsus", html)

    def test_repo_config_has_token(self):
        site = config.load()["site"]
        self.assertTrue(site["analytics_enabled"])
        self.assertRegex(site["analytics_token"], r"^[0-9a-f]{32}$")


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


class ProductionLayoutTest(unittest.TestCase):
    """Päris seadistus: avaleht (juurkaust) = Kogu Eesti + kõik liigad; linnad ja tasemed oma kaustas."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        real = config.load()
        cfg = {"site": {"days_ahead": 2, "base_url": "https://example.org/"},  # default_level puudub → 0
               "geo": real["geo"], "source": real["source"]}
        events = [ev(21, 18, "Tallinlased", sport="kasipall", venue="Kalevi spordihall"),
                  ev(21, 19, "Tartlased", sport="kasipall", venue="Tartu Ülikooli spordihoone", city="Tartu"),
                  ev(21, 20, "Esiliigalased", sport="jalgpall", venue="Wismari jalgpallistaadion", level=2)]
        build.render(events, cfg, date(2026, 11, 20), cls.tmp)

    def read(self, rel):
        return (self.tmp / rel).read_text(encoding="utf-8")

    def test_root_is_all_estonia_all_levels(self):
        root = self.read("2026-11-21/index.html")
        for name in ("Tallinlased", "Tartlased", "Esiliigalased"):
            self.assertIn(name, root)
        self.assertIn('data-region="eesti" data-level="0"', root)
        self.assertIn("Kogu Eesti", root)
        self.assertIn('data-index="1"', self.read("index.html"))

    def test_cities_and_levels_in_own_folders(self):
        for rel in ("tallinn/2026-11-21/index.html", "korgliigad/2026-11-21/index.html",
                    "korgliigad/tallinn/2026-11-21/index.html", "esiliigad/tartu/2026-11-21/index.html"):
            self.assertTrue((self.tmp / rel).exists(), rel)
        for old in ("eesti", "koik"):
            self.assertFalse((self.tmp / old).exists(), old)
        self.assertNotIn("Tartlased", self.read("tallinn/2026-11-21/index.html"))
        self.assertNotIn("Esiliigalased", self.read("korgliigad/2026-11-21/index.html"))

    def test_picker_links_from_root(self):
        root = self.read("2026-11-21/index.html")
        self.assertIn('href="../tallinn/2026-11-21/" data-region="tallinn"', root)
        self.assertIn('href="../korgliigad/2026-11-21/" data-level="1"', root)
        self.assertIn('data-default-level="0"', root)
        self.assertIn("&#34;1&#34;: &#34;korgliigad/&#34;", root)   # tasemete kaustad JS-i suunamise jaoks


class EventSportTest(unittest.TestCase):
    """Ürituste alad (motosport, kergejõustik): mitmepäevane üritus, ürituse rida, "võistlusi" sõnastus."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 4, "days_back": 1, "base_url": "https://example.org/"},
               "geo": config.load()["geo"], "source": config.load()["source"]}
        self.multi = new_event(source="t", sport="motosport", league="Motokross", start=datetime(2026, 11, 21),
                               home="SuperCross Tallinn", away="", venue="Saku Suurhall", city="Tallinn",
                               url="https://example.org/sx", time_tbc=True, end=date(2026, 11, 23))
        game = ev(22, 12, "Pallurid", sport="vorkpall")
        build.render([self.multi, game], cfg, date(2026, 11, 21), self.tmp)

    def read(self, rel):
        return (self.tmp / rel).read_text(encoding="utf-8")

    def test_multi_day_event_on_each_day(self):
        first, second, third = (self.read(f"2026-11-{d}/index.html") for d in (21, 22, 23))
        for html in (first, second, third):
            self.assertIn("SuperCross Tallinn", html)
            self.assertIn("21.–23.11 · Motokross · Saku Suurhall", html)
        self.assertNotIn("SuperCross Tallinn", self.read("2026-11-24/index.html"))
        self.assertIn('<b>—:—</b>', first)
        self.assertIn('<b class="dayno">2./3. päev</b>', second)
        self.assertIn('<b class="dayno">3./3. päev</b>', third)
        self.assertNotIn("kellaaeg täpsustamisel", first)
        # kellaajaga mäng enne mitmepäevase ürituse järgmist päeva
        self.assertLess(second.index("Pallurid"), second.index("SuperCross Tallinn"))

    def test_game_page_and_share_text(self):
        html = self.read(f"m/{self.multi.id}/index.html")
        self.assertIn("laupäev, 21. november – esmaspäev, 23. november", html)
        self.assertIn("Võistluse info allika saidil", html)
        self.assertEqual(build.share_text(self.multi),
                         "SuperCross Tallinn: laupäev, 21. november – esmaspäev, 23. november, Saku Suurhall, Tallinn")

    def test_event_sport_wording_when_empty(self):
        html = self.read("index.html")
        self.assertIn("Järgmise kahe nädala jooksul ei ole Eestis kergejõustikuvõistlusi.", html)

    def test_saved_data_unchanged_for_single_day(self):
        self.assertNotIn("end", ev(22, 12, "X").to_dict())
        self.assertEqual(self.multi.to_dict()["end"], "2026-11-23")
        self.assertEqual(type(self.multi).from_dict(self.multi.to_dict()), self.multi)
