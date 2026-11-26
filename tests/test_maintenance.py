import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import maintenance_log as ml
from scripts import report_issues


def ev(d, kind, n, title, note=""):
    return {"date": d, "event": kind, "what": ml.issue_link(n, title, "o/r"), "note": note}


class LogTest(unittest.TestCase):
    def test_record_roundtrip_and_idempotent(self):
        p = Path(tempfile.mkdtemp()) / "M.md"
        events = [ev("2026-11-20", "avatud", 1, "Allikas katki: x"), ev("2026-11-22", "suletud", 1, "Allikas katki: x", "töötab")]
        self.assertTrue(ml.record(events, p))
        self.assertFalse(ml.record(events, p))                       # korduskäivitus ei muuda midagi
        auto, manual = ml.parse(p.read_text(encoding="utf-8"))
        self.assertEqual([(r["date"], r["event"]) for r in auto], [("2026-11-20", "avatud"), ("2026-11-22", "suletud")])
        self.assertEqual(manual, [])

    def test_summary_numbers(self):
        auto = [{"date": "2026-11-20", "event": "avatud", "what": "[#1](u) A", "note": ""},
                {"date": "2026-11-23", "event": "suletud", "what": "[#1](u) A", "note": ""},
                {"date": "2026-11-21", "event": "avatud", "what": "[#2](u) B", "note": ""},
                {"date": "2026-12-01", "event": "avatud", "what": "[#3](u) C", "note": ""}]
        text = "\n".join(ml.summary(auto, []))
        self.assertIn("| 2026-11 | 2 | 1 | 0 |", text)
        self.assertIn("| 2026-12 | 1 | 0 | 0 |", text)
        self.assertIn("| **Kokku** | **3** | **1** | **0** |", text)
        self.assertIn("Praegu avatud automaatseid Issue'sid: **2**", text)   # #2 ja #3
        self.assertIn("3.0 päeva (1 suletud Issue't)", text)

    def test_manual_rows_survive_regeneration(self):
        p = Path(tempfile.mkdtemp()) / "M.md"
        ml.record([ev("2026-11-20", "avatud", 1, "T")], p)
        text = p.read_text(encoding="utf-8").replace(
            "| Kuupäev | Mis oli katki | Parandus |\n|---|---|---|\n",
            "| Kuupäev | Mis oli katki | Parandus |\n|---|---|---|\n| 2026-11-21 | kava_err | URL muutus, PR #99 |\n")
        p.write_text(text, encoding="utf-8")
        ml.record([ev("2026-11-22", "suletud", 1, "T")], p)
        auto, manual = ml.parse(p.read_text(encoding="utf-8"))
        self.assertEqual(manual, [{"date": "2026-11-21", "what": "kava_err", "fix": "URL muutus, PR #99"}])
        self.assertEqual(len(auto), 2)
        self.assertIn("| **Kokku** | **1** | **1** | **1** |", p.read_text(encoding="utf-8"))

    def test_repo_file_is_valid(self):
        auto, manual = ml.parse(ml.PATH.read_text(encoding="utf-8"))
        self.assertGreater(len(auto), 0)
        self.assertEqual(ml.render(auto, manual), ml.PATH.read_text(encoding="utf-8"))   # fail on genereeritud kujul


class ReportIssuesLogTest(unittest.TestCase):
    def test_open_and_close_are_logged(self):
        tmp = Path(tempfile.mkdtemp())
        report = {"date": "2026-12-01", "sources": [{"source": "abc", "status": "failed", "error": "x", "saved": 0},
                                                      {"source": "old", "status": "ok"}],
                  "unknown_venues": []}
        (tmp / "r.json").write_text(json.dumps(report), encoding="utf-8")
        calls = []

        def fake_gh(*args):
            calls.append(args)
            if args[:2] == ("issue", "list"):
                return json.dumps([{"number": 7, "title": "Allikas katki: old", "body": ""}])
            if args[:2] == ("issue", "create"):
                return "https://github.com/o/r/issues/42\n"
            return ""

        log = tmp / "M.md"
        real_record = ml.record
        with mock.patch.object(report_issues, "gh", fake_gh), \
                mock.patch.object(ml, "record", lambda events: real_record(events, log)), \
                mock.patch.dict("os.environ", {"GITHUB_REPOSITORY": "o/r"}):
            self.assertEqual(report_issues.main(["--report", str(tmp / "r.json")]), 0)
        text = log.read_text(encoding="utf-8")
        self.assertIn("| 2026-12-01 | avatud | [#42](https://github.com/o/r/issues/42) Allikas katki: abc |", text)
        self.assertIn("| 2026-12-01 | suletud | [#7](https://github.com/o/r/issues/7) Allikas katki: old |", text)

    def test_dry_run_writes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "r.json").write_text(json.dumps({"date": "2026-12-01", "sources": [
            {"source": "abc", "status": "failed", "error": "x", "saved": 0}], "unknown_venues": []}), encoding="utf-8")
        with mock.patch.object(ml, "record") as rec:
            report_issues.main(["--dry-run", "--report", str(tmp / "r.json")])
        rec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
