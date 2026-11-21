import unittest

from scrapers.model import Event, parse_score


class ScoreTest(unittest.TestCase):
    def test_parse_score(self):
        self.assertEqual(parse_score("3 - 0"), "3-0")
        self.assertEqual(parse_score(" 12 – 7 "), "12-7")
        self.assertEqual(parse_score("-"), "")
        self.assertEqual(parse_score(""), "")

    def test_old_saved_events_without_result_still_load(self):
        d = {"id": "x", "sport": "jalgpall", "league": "L", "start": "2026-11-21T18:00:00+02:00", "home": "A",
             "away": "B", "venue": "V", "city": "Tallinn", "url": "u", "source": "s", "time_tbc": False, "level": 1}
        self.assertEqual(Event.from_dict(d).result, "")


if __name__ == "__main__":
    unittest.main()
