import io
import unittest
import urllib.error
from datetime import date, datetime, timezone

from scrapers import config
from scrapers.http import Fetcher, FetchError
from scrapers.model import TALLINN, Event, new_event
from scrapers.venues import Venues


def sample(**kw):
    base = dict(
        source="test", sport="jaahoki", league="Optibet Hokiliiga",
        start=datetime(2026, 11, 21, 18, 0), home="HC Panter ", away="HC Kyiv Capitals",
        venue="Haabersti jäähall", city="Tallinn", url="https://example.org/g/1",
    )
    base.update(kw)
    return new_event(**base)


class ModelTest(unittest.TestCase):
    def test_naive_time_becomes_tallinn(self):
        e = sample()
        self.assertEqual(e.start.tzinfo, TALLINN)
        self.assertEqual(e.home, "HC Panter")

    def test_id_stable_and_time_independent(self):
        a = sample()
        b = sample(start=datetime(2026, 11, 21, 19, 30))  # kellaaeg muutus, päev sama
        self.assertEqual(a.id, b.id)
        self.assertNotEqual(a.id, sample(away="Teine").id)

    def test_utc_converted(self):
        e = sample(start=datetime(2026, 11, 21, 16, 0, tzinfo=timezone.utc))
        self.assertEqual(e.start.hour, 18)

    def test_roundtrip(self):
        e = sample()
        self.assertEqual(Event.from_dict(e.to_dict()), e)

    def test_unknown_sport_rejected(self):
        with self.assertRaises(ValueError):
            sample(sport="petank")


class VenuesTest(unittest.TestCase):
    def setUp(self):
        self.v = Venues.load()

    def test_alias_with_odd_spelling(self):
        self.assertEqual(self.v.lookup("tallina,  IGAUNIJA").name, "Haabersti jäähall")
        self.assertEqual(self.v.lookup("Audentes Sports Hall").name, "Audentese spordihall")

    def test_city_filter(self):
        self.assertTrue(self.v.is_tallinn("TalTech Spordihall"))
        self.assertFalse(self.v.is_tallinn("Viimsi kooli Spordikeskus"))

    def test_unknown_is_logged(self):
        with self.assertLogs("scrapers.venues", "WARNING"):
            self.assertIsNone(self.v.lookup("Kuu peal asuv saal"))
        self.assertIn("Kuu peal asuv saal", self.v.unknown)


class FakeResp(io.BytesIO):
    class headers:
        @staticmethod
        def get_content_charset():
            return "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FetcherTest(unittest.TestCase):
    def make(self, responses):
        self.sleeps = []
        self.now = [0.0]
        self.requests = []
        it = iter(responses)

        def opener(req, timeout):
            self.requests.append(req)
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return FakeResp(r.encode())

        return Fetcher("test-agent", delay=3, host_delays={"slow.ee": 5}, backoff=1,
                       sleep=self.sleeps.append, clock=lambda: self.now[0], opener=opener)

    def test_user_agent_and_delay(self):
        f = self.make(["a", "b", "c"])
        self.assertEqual(f.get("https://slow.ee/1"), "a")
        f.get("https://slow.ee/2")
        f.get("https://other.ee/1")
        self.assertEqual(self.requests[0].get_header("User-agent"), "test-agent")
        self.assertEqual(self.sleeps, [5])  # paus ainult sama saidi teise päringu ees

    def test_retry_then_success(self):
        f = self.make([urllib.error.URLError("katkes"), "ok"])
        with self.assertLogs("scrapers.http", "WARNING"):
            self.assertEqual(f.get("https://x.ee/"), "ok")

    def test_404_not_retried(self):
        err = urllib.error.HTTPError("https://x.ee/", 404, "Not Found", None, None)
        f = self.make([err, "never"])
        with self.assertRaises(FetchError):
            f.get("https://x.ee/")
        self.assertEqual(len(self.requests), 1)


class ConfigTest(unittest.TestCase):
    def test_loads_and_seasons(self):
        cfg = config.load()
        names = {s["name"] for s in cfg["source"]}
        self.assertIn("jaahoki_optibet", names)
        foot = next(s for s in cfg["source"] if s["sport"] == "jalgpall")
        self.assertFalse(config.in_season(foot, date(2026, 12, 1)))
        self.assertTrue(config.in_season(foot, date(2027, 6, 1)))

    def test_user_agent_contact(self):
        cfg = {"http": {"user_agent": "bot/1 (+https://s.ee)", "contact": "info@s.ee"}}
        self.assertEqual(config.user_agent(cfg), "bot/1 (+https://s.ee; info@s.ee)")


if __name__ == "__main__":
    unittest.main()
