import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import archive
from scrapers.model import TALLINN, new_event


def game(start, venue="Saal A", home="A", away="B"):
    return new_event(source="s", sport="korvpall", league="L", start=start, home=home, away=away,
                     venue=venue, city="Tallinn", url="https://example.org/")


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.d1 = date(2026, 11, 20)
        self.d2 = date(2026, 11, 21)
        self.start = datetime(2026, 12, 5, 18, 0, tzinfo=TALLINN)

    def read(self, year=2026):
        return json.loads((self.root / str(year) / "s.json").read_text(encoding="utf-8"))

    def test_new_game_is_archived(self):
        archive.update("s", [game(self.start)], self.d1, root=self.root)
        rec = next(iter(self.read().values()))
        self.assertEqual(rec["first_seen"], "2026-11-20")
        self.assertEqual(rec["changes"], [])

    def test_unchanged_data_does_not_touch_file(self):
        archive.update("s", [game(self.start)], self.d1, root=self.root)
        path = self.root / "2026" / "s.json"
        before = path.read_text(encoding="utf-8")
        self.assertEqual(archive.update("s", [game(self.start)], self.d2, root=self.root), 0)
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_changes_are_recorded(self):
        archive.update("s", [game(self.start)], self.d1, root=self.root)
        moved = game(self.start.replace(hour=20), venue="Saal B")
        archive.update("s", [moved], self.d2, root=self.root)
        rec = next(iter(self.read().values()))
        fields = {c["field"]: c for c in rec["changes"]}
        self.assertEqual(set(fields), {"start", "venue"})
        self.assertEqual(fields["venue"]["from"], "Saal A")
        self.assertEqual(fields["venue"]["to"], "Saal B")
        self.assertEqual(fields["venue"]["on"], "2026-11-21")
        self.assertEqual(rec["event"]["venue"], "Saal B")

    def test_result_is_recorded_and_old_records_without_result_are_not_a_change(self):
        g = game(self.start)
        archive.update("s", [g], self.d1, root=self.root)
        path = self.root / "2026" / "s.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        del data[g.id]["event"]["result"]  # arhiiv, mis tehti enne tulemuse välja lisamist
        path.write_text(json.dumps(data), encoding="utf-8")
        archive.update("s", [g], self.d2, root=self.root)
        self.assertEqual(self.read()[g.id]["changes"], [])
        played = new_event(source="s", sport="korvpall", league="L", start=self.start, home="A", away="B",
                           venue="Saal A", city="Tallinn", url="https://example.org/", result="3-0")
        archive.update("s", [played], date(2026, 12, 6), root=self.root)
        change = self.read()[g.id]["changes"][0]
        self.assertEqual((change["field"], change["from"], change["to"]), ("result", "", "3-0"))

    def test_vanished_future_game_is_marked_missing_and_unmarked_on_return(self):
        g = game(self.start)
        archive.update("s", [g], self.d1, root=self.root)
        archive.update("s", [], self.d2, root=self.root)
        self.assertEqual(self.read()[g.id]["missing_since"], "2026-11-21")
        archive.update("s", [g], date(2026, 11, 22), root=self.root)
        self.assertNotIn("missing_since", self.read()[g.id])

    def test_partial_fetch_does_not_mark_missing(self):
        g = game(self.start)
        archive.update("s", [g], self.d1, root=self.root)
        archive.update("s", [], self.d2, complete=False, root=self.root)
        self.assertNotIn("missing_since", self.read()[g.id])

    def test_past_game_is_never_marked_missing(self):
        g = game(datetime(2026, 11, 1, 18, tzinfo=TALLINN))
        archive.update("s", [g], date(2026, 10, 30), root=self.root)
        archive.update("s", [], self.d2, root=self.root)
        self.assertNotIn("missing_since", self.read()[g.id])

    def test_games_are_split_by_year(self):
        archive.update("s", [game(self.start), game(datetime(2027, 1, 9, 18, tzinfo=TALLINN))], self.d1,
                       root=self.root)
        self.assertEqual(len(self.read(2026)), 1)
        self.assertEqual(len(self.read(2027)), 1)

    def test_corrupt_file_is_not_overwritten(self):
        path = self.root / "2026" / "s.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ rikutud", encoding="utf-8")
        with self.assertRaises(ValueError):
            archive.update("s", [game(self.start)], self.d1, root=self.root)
        self.assertEqual(path.read_text(encoding="utf-8"), "{ rikutud")


if __name__ == "__main__":
    unittest.main()
