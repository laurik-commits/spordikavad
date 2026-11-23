import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import build
import ulekanded
from scrapers import config, jalgpall_ejl, jalgpall_koondis, kasipall_liigad, kava_delfi, kava_err
from scrapers.http import FetchError
from scrapers.model import TALLINN, Event, new_event

FIX = Path(__file__).parent / "fixtures"
OLD_GEO = dict(config.load()["geo"], default="tallinn")


def ev(day, hour, home, *, sport="vorkpall", league="Balti liiga (mehed)", video="", video_by="", result="",
       venue="Kalevi spordihall"):
    return new_event(source="t", sport=sport, league=league, start=datetime(2026, 11, day, hour, 0), home=home,
                     away="Külalised", venue=venue, city="Tallinn", url="https://example.org/" + home,
                     video=video, video_by=video_by, result=result)


class ModelTest(unittest.TestCase):
    def test_empty_video_not_written(self):
        d = ev(22, 19, "A").to_dict()
        self.assertNotIn("video", d)
        self.assertNotIn("video_by", d)

    def test_video_roundtrip(self):
        e = ev(22, 19, "A", video="https://youtu.be/x", video_by="YouTube")
        d = e.to_dict()
        self.assertEqual((d["video"], d["video_by"]), ("https://youtu.be/x", "YouTube"))
        self.assertEqual(Event.from_dict(d), e)

    def test_name_without_link_is_dropped(self):
        self.assertEqual(ev(22, 19, "A", video_by="YouTube").video_by, "")


class SourceLinksTest(unittest.TestCase):
    def test_kasipall_replay_icons(self):
        men = kasipall_liigad.parse_list((FIX / "kasipall_league_359.html").read_text(encoding="utf-8"))
        women = kasipall_liigad.parse_list((FIX / "kasipall_league_361.html").read_text(encoding="utf-8"))
        by = {g["video_by"] for g in men + women if g["video"]}
        self.assertIn("YouTube", by)
        yt = [g for g in women if g["video_by"] == "YouTube"]
        self.assertTrue(yt)
        self.assertTrue(all(g["video"].startswith("https://www.youtube.com/watch?v=") for g in yt))
        self.assertTrue(all(g["result"] for g in yt))   # järelvaatamine ainult peetud mängudel
        self.assertTrue(any(not g["video"] for g in men + women))
        e = kasipall_liigad.to_event(yt[0], "Kalevi spordihall", "Meistriliiga (naised)")
        self.assertEqual(e.video_by, "YouTube")

    def test_jalgpall_counter_link(self):
        block = ('<div class="actions"><a href="/voistlused/match_info/1" class="button ico-btn info"></a>\n'
                 '<a href="https://www.jalgpall.ee/log/link_counter.php/?id=186106&amp;type=3"\n'
                 '   class="button ico-btn yt"></a></div>')
        self.assertEqual(jalgpall_ejl.video_link(block),
                         "https://www.jalgpall.ee/log/link_counter.php/?id=186106&type=3")
        self.assertEqual(jalgpall_ejl.video_link('<a href="/log/x" class="button ico-btn yt">'),
                         "https://jalgpall.ee/log/x")
        self.assertEqual(jalgpall_ejl.video_link('<a href="/x" class="button ico-btn info">'), "")

    def test_jalgpall_koondis_youtube(self):
        women = jalgpall_koondis.parse((FIX / "jalgpall_koondis_naised.html").read_text(encoding="utf-8"),
                                       "Naiste koondis")
        with_video = [e for e in women if e.video]
        self.assertTrue(with_video)
        self.assertTrue(all(e.video.startswith("https://www.youtube.com/") and e.video_by == "YouTube"
                            for e in with_video))


class LeagueChannelsTest(unittest.TestCase):
    CFG = {"kanal": [{"nimi": "Delfi TV", "url": "https://tv.delfi.ee/"}, {"nimi": "Postimees", "url": "https://tv.postimees.ee/"},
                     {"nimi": "YouTube"}, {"nimi": "ERR", "url": "https://jupiter.err.ee/"}],
           "liiga": [{"sport": "vorkpall", "liigad": ["Balti liiga (mehed)"], "kanalid": ["Delfi TV"]},
                     {"sport": "jalgpall", "liiga_algus": "Meeste koondis", "kanalid": ["ERR"]}]}

    def test_repo_file_is_valid(self):
        self.assertEqual(ulekanded.validate(ulekanded.load()), [])
        self.assertTrue(ulekanded.load().get("kanal"))

    def test_validate_finds_errors(self):
        bad = {"kanal": [{"nimi": "A", "url": "http://a"}, {"nimi": "F", "url": "https://facebook.com/x"}],
               "liiga": [{"sport": "curling", "kanalid": ["B"]}]}
        errors = " | ".join(ulekanded.validate(bad))
        for part in ("https://", "sotsiaalmeedia", "tundmatu ala", "liiga_algus puudub", "'B'"):
            self.assertIn(part, errors)

    def test_manual_first_then_learned_by_count(self):
        events = [ev(10, 19, "A", video="https://p/1", video_by="Postimees"),
                  ev(11, 19, "B", video="https://y/1", video_by="YouTube"),
                  ev(12, 19, "C", video="https://y/2", video_by="YouTube"),
                  ev(25, 19, "D")]
        ch = ulekanded.league_channels(self.CFG, events)[("vorkpall", "Balti liiga (mehed)")]
        self.assertEqual([c["name"] for c in ch], ["Delfi TV", "YouTube", "Postimees"])
        self.assertEqual([c["games"] for c in ch], [0, 2, 1])
        self.assertEqual(ch[0]["url"], "https://tv.delfi.ee/")
        self.assertEqual(ch[1]["url"], "")   # YouTube'il pole üldist linki

    def test_learning_adds_new_league_and_counts_game_once(self):
        e = ev(10, 19, "A", sport="kasipall", league="Meistriliiga (naised)", video="https://y/1", video_by="YouTube")
        ch = ulekanded.league_channels(self.CFG, [e, e])
        self.assertEqual(ch[("kasipall", "Meistriliiga (naised)")], [{"name": "YouTube", "url": "", "games": 1}])

    def test_prefix_and_no_info(self):
        events = [ev(20, 19, "Eesti", sport="jalgpall", league="Meeste koondis: UEFA Rahvuste liiga 2026"),
                  ev(21, 19, "X", sport="saalihoki", league="Meistriliiga")]
        ch = ulekanded.league_channels(self.CFG, events)
        self.assertEqual([c["name"] for c in ch[("jalgpall", "Meeste koondis: UEFA Rahvuste liiga 2026")]], ["ERR"])
        self.assertNotIn(("saalihoki", "Meistriliiga"), ch)

    def test_rows_in_sport_order(self):
        events = [ev(20, 19, "E", sport="kasipall", league="L", video="https://y", video_by="YouTube"),
                  ev(20, 19, "F", sport="jalgpall", league="Meeste koondis: X")]
        rows = ulekanded.rows(ulekanded.league_channels(self.CFG, events))
        self.assertEqual([r["sport"] for r in rows], ["Jalgpall", "Käsipall"])


class CollectVideosTest(unittest.TestCase):
    def test_links_of_dropped_games_are_kept(self):
        import sys
        import types
        from unittest import mock

        from scrapers.venues import Venues

        peetud = new_event(source="fake_video_src", sport="kasipall", league="Meistriliiga (mehed)",
                           start=datetime(2026, 11, 18, 19), home="A", away="B", venue="", city="",
                           url="https://x/1", result="30-28", video="https://www.youtube.com/watch?v=1", video_by="YouTube")
        tulev = new_event(source="fake_video_src", sport="kasipall", league="Meistriliiga (mehed)",
                          start=datetime(2026, 11, 25, 19), home="C", away="D", venue="Kalevi spordihall", city="",
                          url="https://x/2", video="https://www.youtube.com/watch?v=2", video_by="YouTube")
        module = types.ModuleType("scrapers.fake_video_src")
        module.fetch = lambda fetcher: [peetud, tulev]
        cfg = dict(config.load(), source=[{"name": "fake_video_src", "sport": "kasipall", "league": "X", "check": False}])
        videos: dict = {}
        with mock.patch.dict(sys.modules, {"scrapers.fake_video_src": module}), \
                mock.patch.object(build, "save"), mock.patch("archive.update"):
            events, report = build.collect(cfg, Venues.load(), object(), date(2026, 11, 23), videos=videos)
        self.assertEqual([e.id for e in events], [tulev.id])   # saalita mäng andmetesse ei jää
        self.assertEqual(set(videos), {peetud.id})              # aga selle link jääb alles
        self.assertEqual(videos[peetud.id]["video_by"], "YouTube")
        # arhiivist tulev sama mäng saab lingi lehel tagasi
        archived = replace(peetud, video="", video_by="", venue="Kalevi spordihall", city="Tallinn")
        self.assertEqual(ulekanded.apply([archived], videos)[0].video, "https://www.youtube.com/watch?v=1")


class BuildTest(unittest.TestCase):
    def test_dedupe_keeps_first_but_takes_missing_video(self):
        first = ev(22, 19, "A")
        second = new_event(source="u", sport="vorkpall", league="Balti liiga (mehed)", start=datetime(2026, 11, 22, 19),
                           home="A", away="Külalised", venue="Kalevi spordihall", city="Tallinn", url="https://u/",
                           video="https://tv/1", video_by="Delfi TV")
        out, n = build.dedupe([first, second])
        self.assertEqual(n, 1)
        self.assertEqual((out[0].source, out[0].video, out[0].video_by), ("t", "https://tv/1", "Delfi TV"))

    def test_pages_show_watch_links(self):
        past = ev(14, 18, "Peetud", sport="kasipall", league="Meistriliiga (mehed)", result="30-28",
                  video="https://www.youtube.com/watch?v=abc", video_by="YouTube")
        future = ev(22, 19, "Tulev", video="https://tv.delfi.ee/leht/ulekanded-kava", video_by="Delfi TV")
        tv = ev(22, 17, "Teles", sport="korvpall", league="Koondis", video="https://jupiter.err.ee/1", video_by="ERR")
        plain = ev(23, 19, "Tavaline")
        events = [past, future, tv, plain]
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/", "default_level": 1},
               "geo": OLD_GEO, "source": config.load()["source"]}
        out = Path(tempfile.mkdtemp())
        watch = ulekanded.league_channels(LeagueChannelsTest.CFG, events)
        build.render(events, cfg, date(2026, 11, 20), out, watch=watch, channel_types={"ERR": "tv", "Delfi TV": "veeb"})
        read = lambda rel: (out / rel).read_text(encoding="utf-8")  # noqa: E731

        # kolm tüüpi: järelvaatamine (peetud), otseülekanne internetis, teleülekanne; igaühel oma ikoon
        old_day = read("2026-11-14/index.html")
        self.assertIn('class="watch jarel" href="https://www.youtube.com/watch?v=abc"', old_day)
        self.assertIn('title="Järelvaatamine: YouTube"', old_day)
        self.assertIn('class="wi wi-jarel"', old_day)
        day = read("2026-11-22/index.html")
        self.assertIn('class="watch veeb" href="https://tv.delfi.ee/leht/ulekanded-kava" rel="noopener" '
                      'title="Otseülekanne: Delfi TV"', day)
        self.assertIn('class="watch tv" href="https://jupiter.err.ee/1" rel="noopener" title="Teleülekanne: ERR"', day)
        self.assertIn('class="live"', day)   # otseülekande punane täpp
        self.assertNotIn('class="watch ', read("2026-11-23/index.html"))   # lingita mängul ikooni pole

        game = read(f"m/{future.id}/index.html")
        self.assertIn("Otseülekanne: Delfi TV ↗", game)
        self.assertIn('class="btn watch-btn veeb"', game)
        self.assertIn('Selle liiga mänge on näidanud: <a href="https://tv.delfi.ee/" rel="noopener">Delfi TV</a>.', game)
        self.assertIn("Vaata järele: YouTube ↗", read(f"m/{past.id}/index.html"))
        self.assertIn("Teleülekanne: ERR ↗", read(f"m/{tv.id}/index.html"))
        plain_game = read(f"m/{plain.id}/index.html")
        self.assertNotIn("watch-btn", plain_game)
        self.assertIn("Selle liiga mänge on näidanud", plain_game)   # liiga info ka ilma mängu lingita

        info = read("info/index.html")
        self.assertIn('id="ulekanded"', info)
        self.assertIn("Käsipall, Meistriliiga (mehed): YouTube", info)
        for kind in ("tv", "veeb", "jarel"):   # „Meist“ lehel ikoonide selgitus
            self.assertIn(f'class="wi wi-{kind}"', info)

    def test_watch_kind(self):
        types = {"ERR": "tv", "Delfi TV": "veeb", "Vale": "raadio"}
        self.assertEqual(ulekanded.watch_kind("ERR", False, types), "tv")
        self.assertEqual(ulekanded.watch_kind("Delfi TV", False, types), "veeb")
        self.assertEqual(ulekanded.watch_kind("Tundmatu", False, types), "veeb")
        self.assertEqual(ulekanded.watch_kind("Vale", False, types), "veeb")
        self.assertEqual(ulekanded.watch_kind("ERR", True, types), "jarel")
        self.assertEqual(ulekanded.channel_types(ulekanded.load())["ERR"], "tv")
        self.assertIn("tuup", " ".join(ulekanded.validate({"kanal": [{"nimi": "A", "tuup": "raadio"}]})))

    def test_render_without_watch_info(self):
        out = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 1, "base_url": "https://example.org/", "default_level": 1},
               "geo": OLD_GEO, "source": config.load()["source"]}
        e = ev(20, 19, "A")
        build.render([e], cfg, date(2026, 11, 20), out)
        self.assertNotIn("Selle liiga mänge on näidanud", (out / "m" / e.id / "index.html").read_text(encoding="utf-8"))


def game(day, hour, minute, home, away, *, sport="vorkpall", league="Balti liiga (mehed)", tbc=False):
    return new_event(source="t", sport=sport, league=league, start=datetime(2026, month_of(day), day, hour, minute),
                     home=home, away=away, venue="Saal", city="Tallinn", url="https://example.org/", time_tbc=tbc)


def month_of(day):
    return 11 if day >= 20 else 12


class DelfiKavaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = kava_delfi.parse((FIX / "kava_delfi.json").read_text(encoding="utf-8"))

    def test_only_games_with_local_time(self):
        self.assertEqual(len(self.rows), 15)   # 18 rida, neist 3 saadet
        self.assertEqual({r["sport"] for r in self.rows}, {"vorkpall", "korvpall"})
        r = next(r for r in self.rows if r["home"] == "Audentes/Solarstone" and r["away"] == "Barrus Võru VK")
        self.assertEqual(r["start"].strftime("%d.%m %H:%M %z"), "27.11 19:00 +0200")   # 17:00Z
        self.assertEqual((r["url"], r["by"]), (kava_delfi.PAGE, "Delfi TV"))

    def test_hidden_and_shows_skipped(self):
        text = ('{"attributes": {"data": {"streams": ['
                '{"date": {"start": "2026-12-01T17:00:00Z"}, "title": "A - B", "label": "Võrkpall", "hidden": true},'
                '{"date": {"start": "2026-12-01T17:00:00Z"}, "title": "Saade", "label": "Spordisaade"},'
                '{"date": {"start": "2026-12-01T17:00:00Z"}, "title": "C – D", "label": "Käsipall", "url": "https://tv.delfi.ee/x"}]}}}')
        rows = kava_delfi.parse(text)
        self.assertEqual([(r["home"], r["away"], r["sport"], r["url"]) for r in rows],
                         [("C", "D", "kasipall", "https://tv.delfi.ee/x")])
        self.assertEqual(kava_delfi.parse("{}"), [])

    def test_match_real_schedule(self):
        events = [
            game(27, 19, 0, "Audentes/Solarstone", "Barrus Võru VK"),
            game(27, 19, 0, "E-Lux Tallinn", "Eesti Küte/Türi SK", league="Esiliiga (mehed)"),   # sama aeg, teised
            game(28, 19, 0, "PÄRNU Võrkpalliklubi", "Ezerzeme / DU / Homelike"),
            game(24, 19, 0, "Eesti Maaülikool/Embach", "PÄRNU VK", league="Eesti karikas (mehed)"),
            game(5, 18, 0, "BIGBANK Tartu", "PÄRNU Võrkpalliklubi"),
            game(5, 18, 0, "Rae Spordikool/VIASTON", "Kaunas-VDU", league="Balti liiga (naised)"),
            game(6, 13, 0, "Selver x TalTech", "Jēkabpils Lūši"),
            game(2, 19, 30, "Keila KK", "Bigbank/Kalev", sport="korvpall", league="Eesti-Läti Korvpalliliiga"),
            game(5, 18, 0, "Bigbank/Kalev", "Liepaja", sport="korvpall", league="Eesti-Läti Korvpalliliiga"),
            game(2, 0, 0, "PÄRNU VK", "Eesti Maaülikool/Embach", league="Eesti karikas (mehed)", tbc=True),
        ]
        links = ulekanded.match(events, self.rows)
        matched = {(e.home, e.away) for e in events if e.id in links}
        self.assertEqual(matched, {
            ("Audentes/Solarstone", "Barrus Võru VK"), ("PÄRNU Võrkpalliklubi", "Ezerzeme / DU / Homelike"),
            ("Eesti Maaülikool/Embach", "PÄRNU VK"), ("BIGBANK Tartu", "PÄRNU Võrkpalliklubi"),
            ("Rae Spordikool/VIASTON", "Kaunas-VDU"), ("Selver x TalTech", "Jēkabpils Lūši"),
            ("Keila KK", "Bigbank/Kalev"), ("Bigbank/Kalev", "Liepaja")})
        link = links[events[0].id]
        self.assertEqual((link["video_by"], link["league"], link["sport"]), ("Delfi TV", "Balti liiga (mehed)", "vorkpall"))

    def test_time_window_swapped_and_tbc(self):
        row = {"start": datetime(2026, 12, 1, 18, 0, tzinfo=TALLINN), "sport": "kasipall", "home": "Põlva Serviti",
               "away": "Viljandi HC", "url": "https://tv/1", "by": "Delfi TV"}
        near = game(1, 18, 30, "Viljandi HC", "Põlva Serviti", sport="kasipall")   # vahetuses, 30 min
        far = game(1, 20, 0, "Põlva Serviti", "Viljandi HC", sport="kasipall")     # 2 h hiljem
        tbc = game(1, 0, 0, "Põlva Serviti", "Viljandi HC", sport="kasipall", tbc=True)
        self.assertEqual(set(ulekanded.match([near], [row])), {near.id})
        self.assertEqual(ulekanded.match([far], [row]), {})
        self.assertEqual(set(ulekanded.match([tbc], [row])), {tbc.id})

    def test_ambiguous_row_skipped(self):
        row = {"start": datetime(2026, 12, 1, 18, 0, tzinfo=TALLINN), "sport": "vorkpall", "home": "Tartu",
               "away": "Pärnu", "url": "https://tv/1", "by": "Delfi TV"}
        a = game(1, 18, 0, "Tartu", "Pärnu")
        b = game(1, 18, 0, "Tartu VK", "Pärnu VK", league="Eesti karikas (mehed)")
        self.assertEqual(ulekanded.match([a, b], [row]), {})

    def test_generic_words_do_not_match(self):
        row = {"start": datetime(2026, 12, 1, 18, 0, tzinfo=TALLINN), "sport": "korvpall", "home": "Keila Basket",
               "away": "BC Pärnu", "url": "https://tv/1", "by": "Delfi TV"}
        self.assertEqual(ulekanded.match([game(1, 18, 0, "Viimsi Basket", "BC Kalev", sport="korvpall")], [row]), {})


class ErrKavaTest(unittest.TestCase):
    TEXT = (FIX / "kava_err_etv2.json").read_text(encoding="utf-8")

    def test_parse_sport_rows(self):
        rows = kava_err.parse(self.TEXT)
        self.assertEqual([(r["sport"], r["home"], r["away"]) for r in rows], [
            ("suusatamine", "Laskesuusatamise MK-etapp Kontiolahtis. Naiste 15 km", ""),
            ("korvpall", "Eesti", "Prantsusmaa")])
        ball = rows[1]
        self.assertEqual(ball["start"].strftime("%d.%m.%Y %H:%M %z"), "27.11.2026 18:45 +0200")
        self.assertEqual((ball["url"], ball["by"]), ("https://jupiter.err.ee/1610194190/korvpalli-mm-valikmang", "ERR"))

    def test_sport_names_repeats_and_non_games(self):
        self.assertEqual(kava_err.sport_of("Saalijalgpalli meistriliiga. A - B"), "saalijalgpall")
        self.assertEqual(kava_err.sport_of("Jalgpalli Premium liiga. A - B"), "jalgpall")
        self.assertEqual(kava_err.sport_of("WRC Rally Estonia. Kiiruskatse"), "autosport")
        self.assertEqual(kava_err.sport_of("Aktuaalne kaamera"), "")
        text = ('[{"name": "Korvpalli MM-valikmäng. Eesti - Prantsusmaa*", "startTime": 1795797900},'
                ' {"name": "Jalgpalli EM-valiksarja loosimine", "startTime": 1795797900},'
                ' {"name": "Võrkpalli Balti liiga. Tartu - Pärnu (otse)", "startTime": 1795797900, "url": "x"}]')
        rows = kava_err.parse(text)
        self.assertEqual([(r["home"], r["away"], r["url"]) for r in rows], [("Tartu", "Pärnu", kava_err.PAGE)])

    def test_fetch_all_days_and_channels(self):
        class Fake:
            def __init__(self, fail=lambda url: False):
                self.urls, self.fail = [], fail

            def get(self, url):
                self.urls.append(url)
                if self.fail(url):
                    raise FetchError(url)
                return ErrKavaTest.TEXT

        f = Fake()
        rows = kava_err.fetch(f, today=date(2026, 11, 27))
        self.assertEqual(len(f.urls), kava_err.DAYS * len(kava_err.CHANNELS))
        self.assertIn("day=4&month=12&year=2026&channel=etv2", f.urls[-1])
        self.assertEqual(len(rows), 2 * len(f.urls))
        self.assertTrue(kava_err.fetch(Fake(lambda u: "channel=etv2" in u), today=date(2026, 11, 27)))
        with self.assertRaises(FetchError):
            kava_err.fetch(Fake(lambda u: True), today=date(2026, 11, 27))

    def test_match_national_game_and_events(self):
        rows = kava_err.parse(self.TEXT)
        national = new_event(source="kasitsi", sport="korvpall", league="Koondis", start=datetime(2026, 11, 27, 19),
                             home="Eesti", away="Prantsusmaa", venue="Saku Suurhall", city="Tallinn", url="https://x/")
        self.assertEqual(set(ulekanded.match([national], rows)), {national.id})
        mm = new_event(source="kasitsi", sport="suusatamine", league="Laskesuusatamine", start=datetime(2027, 2, 10, 12),
                       home="Laskesuusatamise MM Otepää", away="", venue="Tehvandi", city="Otepää", url="https://x/",
                       end=date(2027, 2, 21))
        stream = {"start": datetime(2027, 2, 12, 15, 0, tzinfo=TALLINN), "sport": "suusatamine",
                  "home": "Laskesuusatamise MM-võistlused Otepääl. Naiste sprint", "away": "", "url": "https://j/1", "by": "ERR"}
        other = dict(stream, home="Laskesuusatamise MK-etapp Kontiolahtis. Naiste sprint")
        late = dict(stream, start=datetime(2027, 2, 25, 15, 0, tzinfo=TALLINN))
        self.assertEqual(set(ulekanded.match([mm], [stream])), {mm.id})
        self.assertEqual(ulekanded.match([mm], [other]), {})   # teine etapp: ainult 1 ühine sõna
        self.assertEqual(ulekanded.match([mm], [late]), {})    # pärast ürituse lõppu


class LinksStoreTest(unittest.TestCase):
    def link(self, day, by="Delfi TV"):
        return {"video": "https://tv/", "video_by": by, "start": f"2026-{month_of(day):02d}-{day:02d}T19:00:00+02:00",
                "sport": "vorkpall", "league": "Balti liiga (mehed)"}

    def test_update_prunes_old_and_cancelled(self):
        today = date(2026, 11, 23)
        old = {"vana": dict(self.link(1), start="2026-04-01T19:00:00+03:00"),   # üle 180 päeva
               "peetud": self.link(21), "tana": self.link(23), "ara": self.link(28),
               "teine": self.link(29, by="ERR")}
        new = {"uus": self.link(30)}
        out = ulekanded.update_links(old, new, today, refreshed={"Delfi TV"})
        self.assertEqual(set(out), {"peetud", "tana", "teine", "uus"})
        # kava lugemine ebaõnnestus → tulevasi seoseid ei kustutata
        self.assertIn("ara", ulekanded.update_links(old, {}, today, refreshed=set()))

    def test_save_only_when_changed_and_apply(self):
        path = Path(tempfile.mkdtemp()) / "data" / "ulekanded.json"
        e = ev(22, 19, "A")
        links = {e.id: self.link(22)}
        ulekanded.save_links(links, path)
        self.assertEqual(ulekanded.load_links(path), links)
        mtime = path.stat().st_mtime_ns
        ulekanded.save_links(dict(links), path)
        self.assertEqual(path.stat().st_mtime_ns, mtime)
        own = ev(23, 19, "B", video="https://youtube.com/x", video_by="YouTube")
        links[own.id] = self.link(23)
        applied = ulekanded.apply([e, own, ev(24, 19, "C")], links)
        self.assertEqual([x.video_by for x in applied], ["Delfi TV", "YouTube", ""])   # allika enda link jääb

    def test_fetch_streams_reports_failure(self):
        class Broken:
            def get(self, url):
                raise RuntimeError("võrk maas")

        class Ok:
            def get(self, url):
                return (FIX / "kava_delfi.json").read_text(encoding="utf-8")

        cfg = {"kanal": [{"nimi": "Delfi TV", "kava": "delfi"}, {"nimi": "YouTube"}]}
        rows, report = ulekanded.fetch_streams(cfg, Broken())
        self.assertEqual((rows, report[0]["status"], report[0]["source"]), ([], "failed", "kava_delfi"))
        rows, report = ulekanded.fetch_streams(cfg, Ok())
        self.assertEqual((len(rows), report[0]["status"], report[0]["fetched"]), (15, "ok", 15))
        self.assertEqual(len(report), 1)   # kavata kanalit ei loeta

    def test_manual_games_become_streams(self):
        cfg = ulekanded.parse('''
[[kanal]]
nimi = "Postimees"
url = "https://tv.postimees.ee/"
[[kanal]]
nimi = "YouTube"
[[mang]]
sport = "kasipall"
algus = 2026-12-01T18:00:00
kodu = "Põlva Serviti"
voorad = "Viljandi HC"
kanal = "Postimees"
url = "https://sport.postimees.ee/1/otse"
[[mang]]
sport = "kasipall"
algus = 2026-12-02T18:00:00
kodu = "A"
kanal = "YouTube"
url = "https://www.youtube.com/watch?v=x"
''')
        self.assertEqual(ulekanded.validate(cfg), [])
        streams = ulekanded.manual_streams(cfg)
        self.assertEqual(streams[0]["start"], datetime(2026, 12, 1, 18, 0, tzinfo=TALLINN))
        self.assertEqual((streams[0]["by"], streams[1]["away"]), ("Postimees", ""))
        e = game(1, 18, 0, "Põlva Serviti", "Viljandi HC", sport="kasipall", league="Meistriliiga (mehed)")
        self.assertEqual(ulekanded.match([e], streams)[e.id]["video_by"], "Postimees")
        bad = dict(cfg, mang=[dict(cfg["mang"][0], url="https://facebook.com/x"),
                              dict(cfg["mang"][1], url="https://vimeo.com/x"), {"sport": "kasipall"}])
        errors = " | ".join(ulekanded.validate(bad))
        self.assertEqual(errors.count("kanali"), 2)
        self.assertIn("algus peab olema", errors)
        self.assertIn("kodu puudub", errors)

    def test_repo_channels_have_readers(self):
        kavas = {k["nimi"]: k.get("kava") for k in ulekanded.load()["kanal"]}
        self.assertEqual((kavas["Delfi TV"], kavas["ERR"]), ("delfi", "err"))


if __name__ == "__main__":
    unittest.main()
