import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import build
import ulekanded
from scrapers import config, jalgpall_ejl, jalgpall_koondis, kasipall_liigad
from scrapers.model import Event, new_event

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
        plain = ev(23, 19, "Tavaline")
        events = [past, future, plain]
        cfg = {"site": {"days_ahead": 3, "base_url": "https://example.org/sk/", "default_level": 1},
               "geo": OLD_GEO, "source": config.load()["source"]}
        out = Path(tempfile.mkdtemp())
        watch = ulekanded.league_channels(LeagueChannelsTest.CFG, events)
        build.render(events, cfg, date(2026, 11, 20), out, watch=watch)
        read = lambda rel: (out / rel).read_text(encoding="utf-8")  # noqa: E731

        old_day = read("2026-11-14/index.html")
        self.assertIn('class="watch" href="https://www.youtube.com/watch?v=abc"', old_day)
        self.assertIn('title="Vaata järele: YouTube"', old_day)
        day = read("2026-11-22/index.html")
        self.assertIn('title="Otse: Delfi TV"', day)
        self.assertNotIn('class="watch"', read("2026-11-23/index.html"))   # lingita mängul ikooni pole

        game = read(f"m/{future.id}/index.html")
        self.assertIn("▶ Otse: Delfi TV ↗", game)
        self.assertIn('Selle liiga mänge on näidanud: <a href="https://tv.delfi.ee/" rel="noopener">Delfi TV</a>.', game)
        self.assertIn("▶ Vaata järele: YouTube ↗", read(f"m/{past.id}/index.html"))
        plain_game = read(f"m/{plain.id}/index.html")
        self.assertNotIn("watch-btn", plain_game)
        self.assertIn("Selle liiga mänge on näidanud", plain_game)   # liiga info ka ilma mängu lingita

        info = read("info/index.html")
        self.assertIn('id="ulekanded"', info)
        self.assertIn("Käsipall, Meistriliiga (mehed): YouTube", info)

    def test_render_without_watch_info(self):
        out = Path(tempfile.mkdtemp())
        cfg = {"site": {"days_ahead": 1, "base_url": "https://example.org/", "default_level": 1},
               "geo": OLD_GEO, "source": config.load()["source"]}
        e = ev(20, 19, "A")
        build.render([e], cfg, date(2026, 11, 20), out)
        self.assertNotIn("Selle liiga mänge on näidanud", (out / "m" / e.id / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
