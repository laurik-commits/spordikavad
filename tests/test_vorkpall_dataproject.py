import unittest
from datetime import datetime
from pathlib import Path

from scrapers import config
from scrapers import vorkpall_dataproject as adapter
from scrapers.model import TALLINN
from scrapers.venues import Venues

FIX = Path(__file__).parent / "fixtures"

COMPS = {c["league"]: c for c in next(s for s in config.load()["source"] if s["name"] == adapter.NAME)["competitions"]}
FILES = {
    "Balti liiga (mehed)": "vorkpall_bvl_mehed.html",
    "Balti liiga (naised)": "vorkpall_bvl_naised.html",
    "Meistriliiga (mehed)": "vorkpall_evf_mehed_emv.html",
    "Meistriliiga (naised)": "vorkpall_evf_naised_ml.html",
    "Eesti karikas (mehed)": "vorkpall_evf_mehed_karikas.html",
    "Eesti karikas (naised)": "vorkpall_evf_naised_karikas.html",
}


def parse(league):
    return adapter.parse((FIX / FILES[league]).read_text(encoding="utf-8"), COMPS[league])


class FakeFetcher:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        league = next(l for l, c in COMPS.items() if url == adapter.matches_url(c))
        return (FIX / FILES[league]).read_text(encoding="utf-8")


TOP = [c for l, c in COMPS.items() if l in FILES]  # kõrgliigad, millel on fixture


class VorkpallDataprojectTest(unittest.TestCase):
    def test_counts_per_competition(self):
        counts = {l: len(parse(l)) for l in FILES}
        self.assertEqual(counts, {
            "Balti liiga (mehed)": 38, "Balti liiga (naised)": 42, "Meistriliiga (mehed)": 0,
            "Meistriliiga (naised)": 19, "Eesti karikas (mehed)": 16, "Eesti karikas (naised)": 9,
        })

    def test_mens_baltic_home_game(self):
        e = next(e for e in parse("Balti liiga (mehed)") if e.home == "Audentes/Solarstone" and e.away == "Barrus Võru VK")
        self.assertEqual(e.start, datetime(2026, 11, 27, 19, 0, tzinfo=TALLINN))
        self.assertEqual(e.url, "https://bvl-web.dataproject.com/MatchStatistics.aspx?mID=1659&ID=29&PID=30")

    def test_womens_league_game_in_tallinn(self):
        e = next(e for e in parse("Meistriliiga (naised)") if e.home == "TalTech/Nordaid")
        self.assertEqual(e.league, "Meistriliiga (naised)")
        self.assertTrue(e.url.startswith("https://evf-web.dataproject.com/MatchStatistics.aspx?mID="))
        self.assertTrue(e.url.endswith("&ID=97&PID=147"))

    def test_url_without_pid(self):
        self.assertEqual(adapter.matches_url(COMPS["Meistriliiga (mehed)"]),
                         "https://evf-web.dataproject.com/CompetitionMatches.aspx?ID=96")

    def test_fetch_uses_all_configured_competitions(self):
        f = FakeFetcher()
        src = {"competitions": TOP}
        events = adapter.fetch(f, source=src)
        self.assertEqual(len(f.urls), 6)
        self.assertEqual(len(events), 124)
        self.assertEqual(len({e.id for e in events}), 124)

    def test_all_venues_known(self):
        v = Venues.load()
        unknown = {e.venue for l in FILES for e in parse(l) if v.lookup(e.venue) is None}
        self.assertEqual(unknown, set())

    def test_level_from_config(self):
        self.assertEqual({e.level for e in parse("Balti liiga (mehed)")}, {1})
        esiliiga = dict(COMPS["Balti liiga (mehed)"], level=2)
        page = (FIX / FILES["Balti liiga (mehed)"]).read_text(encoding="utf-8")
        self.assertEqual({e.level for e in adapter.parse(page, esiliiga)}, {2})
        self.assertEqual(COMPS["Esiliiga (mehed)"]["level"], 2)

    def test_results_are_sets_won_for_played_games_only(self):
        events = parse("Balti liiga (mehed)")
        played = [e for e in events if e.result]
        self.assertEqual(len(played), 19)   # enne parandust 18: nihke tõttu kadus esimese mängu tulemus
        self.assertTrue(all(e.start.date().isoformat() <= "2026-11-14" for e in played))
        # võitja on võitnud 3 setti, kaotaja alla selle
        for e in played:
            home, guest = map(int, e.result.split("-"))
            self.assertEqual(max(home, guest), 3)
            self.assertLess(min(home, guest), 3)
        # mängimata mängul tulemust ei ole (DataProject näitab seal 0-0)
        self.assertTrue(all(e.result == "" for e in events if e.start.date().isoformat() > "2026-11-14"))

    def test_result_is_home_first(self):
        e = next(e for e in parse("Balti liiga (naised)") if e.result == "2-3")
        self.assertEqual(e.result, "2-3")

    def test_every_row_gets_its_own_result_not_the_neighbours(self):
        """Regressioon (2026-11-28): HTML-is on igal plokil lõpus KÕRVAL OLEVA rea peidetud väljad HF_WonSet*; adapter andis seetõttu igale mängule
        järgmise mängu tulemuse. Kontroll kahe sõltumatu allikaga: rea nähtav tulemus peab võrduma sama rea peidetud väljadega (täis id järgi)."""
        import re
        checked = 0
        for league, name in FILES.items():
            page = (FIX / name).read_text(encoding="utf-8")
            won = {}
            for side in ("Home", "Guest"):
                for m in re.finditer(r'id="([^"]*RADLIST_Matches_ctrl\d+)_HF_WonSet' + side + r'"[^>]*\svalue="(\d*)"', page):
                    won.setdefault(m.group(1), {})[side] = m.group(2)
            starts = [m.start() for m in adapter._ROW_START.finditer(page)] + [len(page)]
            for a_, b_ in zip(starts, starts[1:]):
                block = page[a_:b_]
                key = re.search(r'id="([^"]*RADLIST_Matches_ctrl\d+)_MatchRow"', block).group(1)
                h, g = won.get(key, {}).get("Home", ""), won.get(key, {}).get("Guest", "")
                truth = f"{int(h)}-{int(g)}" if h.isdigit() and g.isdigit() and int(h) + int(g) > 0 else ""
                self.assertEqual(adapter._result(block), truth, (league, key))
                checked += 1
        self.assertGreater(checked, 100)

    def test_result_comes_from_the_rows_own_labels_even_if_hidden_fields_belong_to_the_next_row(self):
        # päris elavhaaval (Tallinna Ülikool – E-Lux Tallinn 3:0): rea nähtav tulemus 3-0, ploki lõpus on järgmise rea peidetud väljad 0-3
        row = lambda ctrl, home, away, a, b, hid: (
            f'<div id="x_RADLIST_Matches_ctrl{ctrl}_MatchRow"><span id="x_RADLIST_Matches_ctrl{ctrl}_LB_DataOra">26/11/2026 - 19:45</span>'
            f'<span id="x_RADLIST_Matches_ctrl{ctrl}_Label6">{home}</span><span id="x_RADLIST_Matches_ctrl{ctrl}_Label7">{away}</span>'
            f'<span id="x_RADLIST_Matches_ctrl{ctrl}_LB_SetCasa">{a}</span><span id="x_RADLIST_Matches_ctrl{ctrl}_LB_SetOspiti">{b}</span>'
            f'<a href="MatchStatistics.aspx?mID={ctrl}">x</a>{hid}</div>')
        nxt = lambda ctrl, h, g: (f'<input type="hidden" id="x_RADLIST_Matches_ctrl{ctrl}_HF_WonSetHome" value="{h}" />'
                                  f'<input type="hidden" id="x_RADLIST_Matches_ctrl{ctrl}_HF_WonSetGuest" value="{g}" />')
        page = row(46, "Tallinna Ülikool", "E-Lux Tallinn", 3, 0, nxt(48, 0, 3)) + row(48, "E-Lux Tallinn", "Eesti Küte/Türi SK", 0, 3, nxt(50, 0, 0))
        events = adapter.parse(page, {"host": "evf-web", "id": 98, "pid": 148, "league": "Esiliiga (mehed)"})
        self.assertEqual([(e.home, e.result) for e in events], [("Tallinna Ülikool", "3-0"), ("E-Lux Tallinn", "0-3")])

    def test_no_markup_in_team_names(self):
        self.assertFalse(any("<" in e.home + e.away for l in FILES for e in parse(l)))


if __name__ == "__main__":
    unittest.main()
