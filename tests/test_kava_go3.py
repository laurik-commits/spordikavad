import unittest
from datetime import date, datetime
from pathlib import Path

import ulekanded
from scrapers import kava_go3
from scrapers.http import FetchError
from scrapers.model import TALLINN, new_event

FIX = Path(__file__).parent / "fixtures" / "kava_go3.json"


def game():
    return new_event(source="t", sport="korvpall", league="Meeste koondis: MM-valiksari", start=datetime(2026, 11, 27, 19, 0),
                     home="Eesti", away="Prantsusmaa", venue="Saku Suurhall", city="Tallinn", url="https://x.ee/")


class Go3Test(unittest.TestCase):
    def test_parse_live_only(self):
        # otseülekanne Go3 Sport 2-s; kordus (liveProgramme false) ja vahepaus jäävad välja
        rows = kava_go3.parse(FIX.read_text(encoding="utf-8"))
        self.assertEqual([(r["sport"], r["home"], r["away"], r["by"], r["url"]) for r in rows],
                         [("korvpall", "Eesti", "Prantsusmaa", kava_go3.BY, kava_go3.PAGE)])
        self.assertEqual(rows[0]["start"], datetime(2026, 11, 27, 18, 50, tzinfo=TALLINN))

    def test_error_response(self):
        with self.assertRaises(ValueError):
            kava_go3.parse('{"code": "LIVE_PROGRAMME_INVALID_TIMESPAN"}')

    def test_day_url_tallinn_offset(self):
        self.assertIn("since=2026-11-27T00%3A00%2B0200", kava_go3.day_url(date(2026, 11, 27)))
        self.assertIn("since=2027-07-01T00%3A00%2B0300", kava_go3.day_url(date(2027, 7, 1)))

    def test_fetch_all_failed(self):
        class Fake:
            def get(self, url):
                raise FetchError("x")
        with self.assertRaises(FetchError):
            kava_go3.fetch(Fake(), today=date(2026, 11, 27))

    def test_two_channels_free_first(self):
        e = game()
        start = datetime(2026, 11, 27, 18, 45, tzinfo=TALLINN)
        err = {"start": start, "sport": "korvpall", "home": "Eesti", "away": "Prantsusmaa", "url": "https://jupiter.err.ee/", "by": "ERR"}
        go3 = dict(err, url=kava_go3.PAGE, by=kava_go3.BY)
        links = ulekanded.match([e], [err, go3, go3])
        self.assertEqual(links[e.id]["video_by"], "ERR")
        self.assertEqual(links[e.id]["also"], [{"video": kava_go3.PAGE, "video_by": kava_go3.BY}])
        self.assertEqual(ulekanded.also(links), {e.id: links[e.id]["also"]})


if __name__ == "__main__":
    unittest.main()
