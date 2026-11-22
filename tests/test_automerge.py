import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import automerge_check as am  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = (ROOT / "config.toml").read_text(encoding="utf-8")
VENUES = (ROOT / "venues.toml").read_text(encoding="utf-8")
TODAY = date(2026, 11, 22)
UA = "spordikavad-bot/test"

ENTRY = '''
[[event]]
sport = "korvpall"
league = "Sõprusmäng"
level = 1
kind = "sõprusmäng"
start = 2026-12-05T18:00:00
home = "BC Kalev/Cramo"
away = "Tartu Ülikool"
venue = "Kalevi spordihall"
url = "https://klubi.ee/uudised/sopruskohtumine"
added = 2026-11-22
note = "klubi uudis, kellaaeg kinnitatud"
'''

PAGE = ("<html><body><h1>Sõpruskohtumine</h1><p>Laupäeval, 5. detsembril kell 18.00 kohtuvad Kalevi "
        "spordihallis <b>BC Kalev/Cramo</b> ja Tartu Ülikool.</p></body></html>")


def fake_get(pages: dict):
    def get(url):
        return pages.get(url, (404, ""))
    return get


def run(head_kasitsi, base_kasitsi="", changed=("kasitsi.toml",), pages=None, head_venues=VENUES,
        head_config=CONFIG):
    base = {"config.toml": CONFIG, "venues.toml": VENUES, "kasitsi.toml": base_kasitsi}
    head = {"config.toml": head_config, "venues.toml": head_venues, "kasitsi.toml": head_kasitsi}
    pages = pages if pages is not None else {"https://klubi.ee/uudised/sopruskohtumine": (200, PAGE)}
    return am.evaluate(list(changed), base.get, head.get, TODAY, fake_get(pages), UA)


class GateTest(unittest.TestCase):
    def test_good_pr_passes(self):
        self.assertEqual(run(ENTRY), [])

    def test_only_allowed_files(self):
        problems = run(ENTRY, changed=("kasitsi.toml", "scripts/automerge_check.py"))
        self.assertIn("scripts/automerge_check.py", problems[0])
        self.assertTrue(run(ENTRY, changed=(".github/workflows/automerge.yml",)))

    def test_entry_rules(self):
        cases = {
            "start = 2026-12-05T18:00:00": ("start = 2027-03-01T18:00:00", "pole tänasest 60 päeva sees"),
            "added = 2026-11-22": ("added = 2026-11-01", "added = 2026-11-01"),
            'note = "klubi uudis, kellaaeg kinnitatud"\n': ("", "puudub note"),
            'venue = "Kalevi spordihall"': ('venue = "Tundmatu hall"', "puudub venues.toml-ist"),
        }
        for old, (new, message) in cases.items():
            with self.subTest(message=message):
                problems = run(ENTRY.replace(old, new))
                self.assertTrue(any(message in p for p in problems), problems)

    def test_invalid_file_and_limits(self):
        self.assertIn("tundmatu ala", run(ENTRY.replace('"korvpall"', '"kurling"'))[0])
        many = "".join(ENTRY.replace("BC Kalev/Cramo", f"Klubi {i}") for i in range(11))
        self.assertTrue(any("uusi kirjeid 11" in p for p in run(many)))

    def test_existing_entries_not_changed_and_only_old_removed(self):
        old = ENTRY.replace("2026-12-05", "2026-10-01").replace("BC Kalev/Cramo", "Vana")
        recent = ENTRY.replace("2026-12-05", "2026-11-10").replace("BC Kalev/Cramo", "Hiljutine")
        self.assertEqual(run(ENTRY, base_kasitsi=old), [])                         # vana eemaldus OK
        self.assertTrue(any("pole üle 30 päeva vana" in p for p in run(ENTRY, base_kasitsi=recent)))
        changed = ENTRY.replace("Kalevi spordihall", "Saku Suurhall")
        problems = run(changed + ENTRY.replace("BC Kalev/Cramo", "Uus"), base_kasitsi=ENTRY)
        self.assertTrue(any("muudetud" in p for p in problems), problems)
        self.assertTrue(any("pole uusi" in p for p in run("", base_kasitsi=old)))   # ainult eemaldus

    def test_source_page_must_confirm_date_and_team(self):
        url = "https://klubi.ee/uudised/sopruskohtumine"
        wrong_day = PAGE.replace("5. detsembril", "6. detsembril")
        self.assertTrue(any("kuupäeva" in p for p in run(ENTRY, pages={url: (200, wrong_day)})))
        no_team = PAGE.replace("BC Kalev/Cramo", "keegi").replace("Tartu Ülikool", "keegi teine")
        self.assertTrue(any("nime" in p for p in run(ENTRY, pages={url: (200, no_team)})))
        self.assertTrue(any("ei vasta (404)" in p for p in run(ENTRY, pages={})))

    def test_robots_txt_respected(self):
        url = "https://klubi.ee/uudised/sopruskohtumine"
        robots = (200, "User-agent: *\nDisallow: /uudised/\n")
        problems = run(ENTRY, pages={url: (200, PAGE), "https://klubi.ee/robots.txt": robots})
        self.assertTrue(any("robots.txt keelab" in p for p in problems))
        self.assertTrue(any("robots.txt-i ei saanud" in p
                            for p in run(ENTRY, pages={url: (200, PAGE), "https://klubi.ee/robots.txt": (0, "x")})))

    def test_new_venue_and_place(self):
        venue = '\n[[venue]]\nname = "Uus hall"\ncity = "Kose"\n'
        entry = ENTRY.replace('venue = "Kalevi spordihall"', 'venue = "Uus hall"')
        page = PAGE
        self.assertEqual(run(entry, changed=("kasitsi.toml", "venues.toml"), head_venues=VENUES + venue,
                             pages={"https://klubi.ee/uudised/sopruskohtumine": (200, page)}), [])
        foreign = venue.replace("Kose", "Riia")
        self.assertTrue(any("pole Eestis" in p for p in run(entry, changed=("kasitsi.toml", "venues.toml"),
                                                           head_venues=VENUES + foreign)))
        renamed = VENUES.replace('name = "A. Le Coq Arena"', 'name = "Lilleküla"', 1)
        self.assertTrue(any("muutus või kadus" in p for p in run(ENTRY, changed=("kasitsi.toml", "venues.toml"),
                                                                head_venues=renamed)))

    def test_config_only_new_places(self):
        added = CONFIG.replace('"Mulgi vald" = "Viljandimaa"', '"Mulgi vald" = "Viljandimaa"\n"Kuuli" = "Harjumaa"')
        self.assertEqual(am.check_config(CONFIG, added), [])
        bad_county = CONFIG.replace('"Mulgi vald" = "Viljandimaa"', '"Mulgi vald" = "Viljandimaa"\n"X" = "Kuumaa"')
        self.assertTrue(am.check_config(CONFIG, bad_county))
        other = CONFIG.replace("days_ahead = 14", "days_ahead = 30")
        self.assertTrue(any("muud" in p for p in am.check_config(CONFIG, other)))


class PageMatchTest(unittest.TestCase):
    def test_date_formats(self):
        d = date(2026, 12, 5)
        for text in ["05.12.2026", "5.12 kell 18", "5. detsembril", "laupäev, 5. detsember",
                     "2026-12-05", "Saturday 5 December", "December 5, 2026", "05/12/2026", "5th Dec"]:
            with self.subTest(text=text):
                self.assertTrue(am.date_found(am._norm(text), d))
        for text in ["15.12.2026", "5.11", "25. detsember", "6. detsember"]:
            with self.subTest(text=text):
                self.assertFalse(am.date_found(am._norm(text), d))

    def test_name_matching(self):
        text = am._norm("Eesti U-16 neiud kohtuvad Läti U 16 koondisega")
        self.assertTrue(am.name_found(text, "Eesti U16"))
        self.assertTrue(am.name_found(text, "Läti U16"))
        self.assertFalse(am.name_found(text, "Leedu U16"))


if __name__ == "__main__":
    unittest.main()
