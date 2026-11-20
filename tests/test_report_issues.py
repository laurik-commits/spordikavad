import unittest

from scripts.report_issues import NO_VENUE_TITLE, VENUE_TITLE, _list_body, plan, title_for


def report(*sources, unknown=(), no_venue=None):
    srcs = [{"source": n, "status": s, "error": "x", "saved": 3} for n, s in sources]
    if no_venue:
        srcs[0]["no_venue"] = list(no_venue)
    return {"date": "2026-11-20", "unknown_venues": list(unknown), "sources": srcs}


class PlanTest(unittest.TestCase):
    def test_opens_once_per_broken_source(self):
        to_open, to_close, _ = plan(report(("a", "failed"), ("b", "empty"), ("c", "ok"), ("d", "partial")), set())
        self.assertEqual([t for t, _ in to_open], [title_for("a"), title_for("b"), title_for("d")])
        self.assertEqual(to_close, [])

    def test_partial_mentions_other_competitions_still_update(self):
        to_open, _, _ = plan(report(("d", "partial")), set())
        self.assertIn("Ülejäänud võistlused uuenevad", to_open[0][1])

    def test_no_duplicate_when_already_open(self):
        to_open, _, _ = plan(report(("a", "failed")), {title_for("a")})
        self.assertEqual(to_open, [])

    def test_closes_when_recovered(self):
        _, to_close, _ = plan(report(("a", "ok")), {title_for("a")})
        self.assertEqual(to_close, [title_for("a")])

    def test_offline_or_no_adapter_does_not_close(self):
        _, to_close, _ = plan(report(("a", "offline"), ("b", "no_adapter")), {title_for("a"), title_for("b")})
        self.assertEqual(to_close, [])

    def test_unknown_venues_issue(self):
        to_open, _, _ = plan(report(("a", "ok"), unknown=["Uus saal"]), set())
        self.assertEqual(to_open[0][0], VENUE_TITLE)
        self.assertIn("Uus saal", to_open[0][1])

    def test_unknown_venues_issue_closes_when_resolved(self):
        _, to_close, _ = plan(report(("a", "ok")), {VENUE_TITLE})
        self.assertEqual(to_close, [VENUE_TITLE])

    def test_open_issue_updated_only_when_list_changes(self):
        r = report(("a", "ok"), unknown=["Saal A", "Saal B"])
        to_open, _, to_update = plan(r, {VENUE_TITLE: "vana sisu\n\n- Saal A"})
        self.assertEqual(to_open, [])
        self.assertEqual(to_update[0][0], VENUE_TITLE)
        self.assertIn("Saal B", to_update[0][1])
        # sama sisu → uuendust pole
        _, _, to_update = plan(r, {VENUE_TITLE: to_update[0][1]})
        self.assertEqual(to_update, [])

    def test_games_without_venue_issue(self):
        to_open, _, _ = plan(report(("a", "ok"), no_venue=["25.11 19:00 A – B (Liiga)"]), set())
        self.assertEqual(to_open[0][0], NO_VENUE_TITLE)
        _, to_close, _ = plan(report(("a", "ok")), {NO_VENUE_TITLE})
        self.assertEqual(to_close, [NO_VENUE_TITLE])


if __name__ == "__main__":
    unittest.main()
