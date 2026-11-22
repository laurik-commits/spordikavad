import unittest

import allikad


def item(**over):
    base = {"nimi": "Hall", "liik": "hall", "url": "https://hall.ee/kalender", "alad": ["kõik"],
            "piirkond": "Tallinn", "kuju": "html", "robots": "lubatud", "kasutus": "agent",
            "kontrollitud": __import__("datetime").date(2026, 11, 22)}
    base.update(over)
    return {k: v for k, v in base.items() if v is not None}


class RegisterTest(unittest.TestCase):
    def test_repo_file_is_valid(self):
        items = allikad.load()
        self.assertGreaterEqual(len(items), 40)
        self.assertEqual(allikad.check(items), [])
        # adapterid, mida register nimetab, on olemas ja keelatud allikad on märgitud
        uses = {i["kasutus"] for i in items}
        self.assertIn("adapter:korvpall_kalev", uses)
        basket = next(i for i in items if "basket.ee" in i["url"])
        self.assertEqual(basket["kasutus"], "keelatud")

    def test_rules(self):
        cases = {
            "puudub 'url'": item(url=None),
            "tundmatu liik": item(liik="baar"),
            "tundmatu kuju": item(kuju="flash"),
            "alad peab olema": item(alad=["kurling"]),
            "sotsiaalmeedia": item(url="https://www.facebook.com/hall"),
            "adapterit 'puudub'": item(kasutus="adapter:puudub"),
            "kasutus peab olema \"keelatud\"": item(robots="keelatud", kasutus="agent"),
            "kontrollitud peab olema kuupäev": item(kontrollitud="eile"),
            "tundmatu väli": item(linn="Tallinn"),
        }
        for message, it in cases.items():
            with self.subTest(message=message):
                errors = allikad.check([it], known_adapters={"korvpall_kalev"})
                self.assertTrue(any(message in e for e in errors), errors)

    def test_duplicate_url(self):
        errors = allikad.check([item(), item(nimi="Teine", url="https://hall.ee/kalender/")], set())
        self.assertTrue(any("sama url" in e for e in errors))

    def test_good_item(self):
        self.assertEqual(allikad.check([item(kandidaat=True, markus="ok")], set()), [])


if __name__ == "__main__":
    unittest.main()
