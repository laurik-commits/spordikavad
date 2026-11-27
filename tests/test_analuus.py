"""Analüüs: tulemuste ühtlustus, meeskonnanimed, lugude detektor ja nädalaraport."""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from analuus import lood, nadalaraport, tulemus as tul
from analuus.meeskonnad import Teams
from scrapers.model import TALLINN, new_event

D0 = date(2026, 10, 1)


def ev(day, home, away, result, sport="jalgpall", league="Liiga", level=1):
    d = D0 + timedelta(days=day)
    return new_event(source="t", sport=sport, league=league, start=datetime(d.year, d.month, d.day, 18, 0, tzinfo=TALLINN),
                     home=home, away=away, venue="Koht", city="Tallinn", url="https://example.org/", result=result, level=level)


def prep(events):
    teams = Teams().fit(events)
    return lood.mangud(events, teams)


def liiga_8(extra=()):
    """8 meeskonda: T1–T4 tugevad (võidavad kõik T5–T8 vastu), 16 mängu; lisaks `extra`."""
    ev_, day = [], 0
    for s in "1234":
        for w in "5678":
            ev_.append(ev(day, f"T{s}", f"T{w}", "2-0"))
            day += 1
    return ev_ + list(extra)


class TulemusTest(unittest.TestCase):
    def test_parse_and_terms(self):
        t = tul.parse("jaahoki", "4-5 OT")
        self.assertEqual((t.kodu, t.kylaline, t.lisa, t.vahe, t.kokku, tul.voitja(t)), (4, 5, "OT", 1, 9, "külaline"))
        self.assertEqual(tul.voitja(tul.parse("jalgpall", "1-1")), "viik")
        self.assertIsNone(tul.parse("korvpall", "80-80"))        # korvpallis viiki ei ole: andmeviga
        self.assertIsNone(tul.parse("tennis", "1-0"))            # ala ilma tulemusteta
        self.assertIsNone(tul.parse("jalgpall", ""))
        self.assertIsNone(tul.parse("jalgpall", "abc"))

    def test_points_by_sport(self):
        self.assertEqual(tul.liigapunktid("jalgpall", tul.parse("jalgpall", "2-1")), (3, 0))
        self.assertEqual(tul.liigapunktid("jalgpall", tul.parse("jalgpall", "1-1")), (1, 1))
        self.assertEqual(tul.liigapunktid("vorkpall", tul.parse("vorkpall", "3-2")), (2, 1))
        self.assertEqual(tul.liigapunktid("vorkpall", tul.parse("vorkpall", "0-3")), (0, 3))
        self.assertEqual(tul.liigapunktid("jaahoki", tul.parse("jaahoki", "4-5 OT")), (1, 2))
        self.assertEqual(tul.liigapunktid("korvpall", tul.parse("korvpall", "70-80")), (0, 2))

    def test_close_games_per_sport(self):
        self.assertTrue(tul.tasavagine("jalgpall", tul.parse("jalgpall", "2-2")))
        self.assertFalse(tul.tasavagine("jalgpall", tul.parse("jalgpall", "0-0")))     # null-null pole „tasavägine“ lugu
        self.assertTrue(tul.tasavagine("jalgpall", tul.parse("jalgpall", "3-2")))
        self.assertFalse(tul.tasavagine("jalgpall", tul.parse("jalgpall", "1-0")))
        self.assertTrue(tul.tasavagine("vorkpall", tul.parse("vorkpall", "2-3")))
        self.assertFalse(tul.tasavagine("vorkpall", tul.parse("vorkpall", "3-1")))
        self.assertTrue(tul.tasavagine("korvpall", tul.parse("korvpall", "83-81")))
        self.assertFalse(tul.tasavagine("korvpall", tul.parse("korvpall", "83-70")))
        self.assertEqual(tul.tasavagine("jaahoki", tul.parse("jaahoki", "4-5 OT")), "lisaaeg")


class MeeskonnadTest(unittest.TestCase):
    def test_automatic_unification(self):
        evs = [ev(0, "BARRUS/Võru VK", "Teine", "3-0", "vorkpall"), ev(1, "Barrus Võru VK", "Teine", "3-1", "vorkpall"),
               ev(2, "Barrus/Võru VK", "Kolmas", "3-2", "vorkpall")]
        t = Teams().fit(evs)
        self.assertEqual(len({t.canonical("vorkpall", n) for n in ("BARRUS/Võru VK", "Barrus Võru VK", "Barrus/Võru VK")}), 1)

    def test_youth_and_second_teams_stay_separate(self):
        t = Teams().fit([ev(0, "Bigbank Tartu", "X", "3-0", "vorkpall"), ev(1, "Bigbank Tartu U-20", "X", "3-0", "vorkpall")])
        self.assertNotEqual(t.canonical("vorkpall", "Bigbank Tartu"), t.canonical("vorkpall", "Bigbank Tartu U-20"))

    def test_aliases_from_file_and_conflicts(self):
        p = Path(tempfile.mkdtemp()) / "m.toml"
        p.write_text('[[meeskond]]\nsport = "korvpall"\nnimi = "Valmiera Glass VIA"\naliased = ["Valmiera"]\n', encoding="utf-8")
        t = Teams.load(p)
        self.assertEqual(t.canonical("korvpall", "Valmiera"), "Valmiera Glass VIA")
        self.assertEqual(t.canonical("jalgpall", "Valmiera"), "Valmiera")          # alias kehtib ainult oma alal
        p.write_text('[[meeskond]]\nsport = "korvpall"\nnimi = "A"\naliased = ["X"]\n\n[[meeskond]]\nsport = "korvpall"\nnimi = "B"\naliased = ["X"]\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            Teams.load(p)

    def test_repo_alias_file_is_valid(self):
        Teams.load()   # loeb repo meeskonnad.toml-i, viskab vea topeltaliase korral


class DetektoridTest(unittest.TestCase):
    def test_upset_found_and_ordinary_results_not(self):
        evs = liiga_8([ev(20, "T1", "T8", "0-1"),        # nõrgim (8.) võidab tugevaima (1.)
                       ev(21, "T2", "T3", "2-1")])       # tugev võidab tugeva: pole üllatus
        ms = prep(evs)
        u = lood.ullatused(ms, D0 + timedelta(days=20), D0 + timedelta(days=21))
        self.assertEqual(len(u), 1)
        self.assertEqual((u[0]["voitja"], u[0]["kaotaja"], u[0]["voitja_koht"], u[0]["kaotaja_koht"]), ("T8", "T1", 8, 1))

    def test_small_or_incomplete_league_has_no_upsets_and_marks_streaks(self):
        evs = [ev(i, "A", "B", "0-1") for i in range(6)] + [ev(10, "C", "A", "1-0")]
        ms = prep(evs)
        self.assertEqual(lood.ullatused(ms, D0, D0 + timedelta(days=30)), [])
        s = lood.seeriad(ms, D0, D0 + timedelta(days=30))
        self.assertTrue(s["jatkub"] and all(not x["usaldusvaarne"] for x in s["jatkub"]))

    def test_streaks_continuing_and_broken(self):
        evs = [ev(i, "A", f"X{i}", "2-0") for i in range(6)]                       # A: 6 võitu (päevad 0–5)
        evs += [ev(i, f"Y{i}", "B", "2-0") for i in range(6, 12)]                  # B: 6 kaotust (päevad 6–11)
        ms = prep(evs)
        # aken päevad 4–11: A seeria katkestus puudub, aga A viimane mäng oli päeval 5 (aknas), B kaotused jätkuvad
        s = lood.seeriad(ms, D0 + timedelta(days=4), D0 + timedelta(days=11))
        kinds = {(x["meeskond"], x["tyyp"], x["pikkus"]) for x in s["jatkub"]}
        self.assertIn(("A", "võidud", 6), kinds)
        self.assertIn(("B", "kaotused", 6), kinds)
        # A kaotab päeval 12: seeria katkeb aknas 12–12
        ms2 = prep(evs + [ev(12, "A", "Z", "0-1")])
        s2 = lood.seeriad(ms2, D0 + timedelta(days=12), D0 + timedelta(days=12))
        self.assertIn(("A", "võidud", 6), {(x["meeskond"], x["tyyp"], x["pikkus"]) for x in s2["katkes"]})

    def test_unbeaten_streak_with_draws_only_for_draw_sports(self):
        evs = [ev(i, "A", f"X{i}", "1-1" if i % 2 else "1-0") for i in range(9)]    # A: 9 mängu kaotuseta
        s = lood.seeriad(prep(evs), D0, D0 + timedelta(days=9))
        self.assertIn(("A", "kaotuseta", 9), {(x["meeskond"], x["tyyp"], x["pikkus"]) for x in s["jatkub"]})
        evs2 = [ev(i, "A", f"X{i}", "81-70", "korvpall") for i in range(9)]
        s2 = lood.seeriad(prep(evs2), D0, D0 + timedelta(days=9))
        self.assertEqual({x["tyyp"] for x in s2["jatkub"]}, {"võidud"})              # korvpallis kaotuseta-seeriat ei ole

    def test_close_games_window_only(self):
        evs = [ev(1, "A", "B", "2-2"), ev(2, "C", "D", "5-0"), ev(40, "E", "F", "3-3")]
        t = lood.tasavagised(prep(evs), D0, D0 + timedelta(days=10))
        self.assertEqual([x["mang"] for x in t], ["A – B 2:2"])

    def test_records_new_vs_tied_and_volleyball(self):
        evs = [ev(i, f"H{i}", f"V{i}", "2-1") for i in range(10)] + [ev(30, "A", "B", "9-0")]
        r = lood.rekordid(prep(evs), D0 + timedelta(days=30), D0 + timedelta(days=36))
        skoor = next(x for x in r if x["ulatus"] == "kõik" and x["kategooria"] == "suurim skoor")
        self.assertEqual((skoor["vaartus"], skoor["uus"]), (9, True))
        r2 = lood.rekordid(prep(evs), D0, D0 + timedelta(days=5))     # 9–0 on hiljem, aknas pole rekordi hoidjat
        self.assertFalse(next(x for x in r2 if x["ulatus"] == "kõik" and x["kategooria"] == "suurim skoor")["uus"])
        vb = [ev(i, f"H{i}", f"V{i}", "3-1", "vorkpall") for i in range(12)]
        self.assertFalse([x for x in lood.rekordid(prep(vb), D0, D0 + timedelta(days=20)) if x["kategooria"] in ("suurim skoor", "suurim vahe")])

    def test_record_scope_tip_only_counts_levels_1_2_5(self):
        evs = [ev(i, f"H{i}", f"V{i}", "1-0", level=1) for i in range(10)] + [ev(i, f"N{i}", f"M{i}", "20-0", level=4) for i in range(10)]
        r = lood.rekordid(prep(evs), D0, D0 + timedelta(days=30))
        by = {(x["ulatus"], x["kategooria"]): x["vaartus"] for x in r}
        self.assertEqual((by[("tipp", "suurim skoor")], by[("kõik", "suurim skoor")]), (1, 20))


class RaportTest(unittest.TestCase):
    def test_last_full_week(self):
        a, b = nadalaraport.viimane_nadal(date(2026, 11, 27))     # reede
        self.assertEqual((a, b), (date(2026, 11, 16), date(2026, 11, 22)))
        self.assertEqual(nadalaraport.viimane_nadal(date(2026, 11, 23)), (date(2026, 11, 16), date(2026, 11, 22)))   # esmaspäev
        self.assertEqual(a.weekday(), 0)

    def test_report_renders_writes_and_is_repeatable(self):
        evs = liiga_8([ev(20, "T1", "T8", "0-1"), ev(21, "T2", "T3", "2-2")])
        a, b = D0 + timedelta(days=20), D0 + timedelta(days=26)
        r = nadalaraport.koosta(evs, Teams().fit(evs), a, b)
        md = nadalaraport.markdown(r)
        for h in ("# Nädalaraport", "## Üllatused", "## Seeriad", "## Katkenud seeriad", "## Tasavägised mängud", "## Rekordid", "## Märkused"):
            self.assertIn(h, md)
        self.assertIn("T8 (8. koht) võitis kohtumises T1 (1. koht)", md)
        out = Path(tempfile.mkdtemp())
        files = nadalaraport.kirjuta(r, out)
        first = [p.read_text(encoding="utf-8") for p in files]
        nadalaraport.kirjuta(r, out)
        self.assertEqual(first, [p.read_text(encoding="utf-8") for p in files])
        self.assertEqual(json.loads(first[1])["nadal"], r["nadal"])

    def test_report_does_not_know_the_future(self):
        evs = [ev(i, f"H{i}", f"V{i}", "2-1") for i in range(10)] + [ev(30, "A", "B", "9-0")]
        teams = Teams().fit(evs)
        vana = nadalaraport.koosta(evs, teams, D0, D0 + timedelta(days=6))
        self.assertNotIn("9", {x["vaartus"] for x in vana["rekordid"] if x["kategooria"] == "suurim skoor"})
        uus = nadalaraport.koosta(evs, teams, D0 + timedelta(days=30), D0 + timedelta(days=36))
        self.assertIn(9, {x["vaartus"] for x in uus["rekordid"] if x["kategooria"] == "suurim skoor" and x["uus"]})

    def test_real_data_smoke(self):
        from analuus.andmed import load_events
        evs = load_events()
        r = nadalaraport.koosta(evs, Teams.load().fit(evs), date(2026, 11, 2), date(2026, 11, 8))
        json.dumps(r, ensure_ascii=False)                       # JSON-sõbralik
        self.assertGreater(r["mange_tulemusega"], 0)
        self.assertTrue(nadalaraport.markdown(r).startswith("# Nädalaraport 2026-W45"))


if __name__ == "__main__":
    unittest.main()
