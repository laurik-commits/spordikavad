import unittest

from scripts.report_issues import VENUE_TITLE, plan, title_for


def report(*sources, unknown=()):
    return {"date": "2026-11-20", "unknown_venues": list(unknown),
            "sources": [{"source": n, "status": s, "error": "x", "saved": 3} for n, s in sources]}


class PlanTest(unittest.TestCase):
    def test_opens_once_per_broken_source(self):
        to_open, to_close = plan(report(("a", "failed"), ("b", "empty"), ("c", "ok")), set())
        self.assertEqual([t for t, _ in to_open], [title_for("a"), title_for("b")])
        self.assertEqual(to_close, [])

    def test_no_duplicate_when_already_open(self):
        to_open, _ = plan(report(("a", "failed")), {title_for("a")})
        self.assertEqual(to_open, [])

    def test_closes_when_recovered(self):
        _, to_close = plan(report(("a", "ok")), {title_for("a")})
        self.assertEqual(to_close, [title_for("a")])

    def test_offline_or_no_adapter_does_not_close(self):
        _, to_close = plan(report(("a", "offline"), ("b", "no_adapter")), {title_for("a"), title_for("b")})
        self.assertEqual(to_close, [])

    def test_unknown_venues_issue_closes_when_resolved(self):
        _, to_close = plan(report(("a", "ok")), {VENUE_TITLE})
        self.assertEqual(to_close, [VENUE_TITLE])
        _, to_close = plan(report(("a", "ok"), unknown=["X"]), {VENUE_TITLE})
        self.assertEqual(to_close, [])

    def test_unknown_venues_issue(self):
        to_open, _ = plan(report(("a", "ok"), unknown=["Uus saal"]), set())
        self.assertEqual(to_open[0][0], VENUE_TITLE)
        self.assertIn("Uus saal", to_open[0][1])


if __name__ == "__main__":
    unittest.main()
