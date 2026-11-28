"""Tulemuste auditi abifunktsioonid (ilma võrguta): tabeli lugemine ja tabeli arvutamine meie tulemustest."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tulemuste_audit as ta  # noqa: E402

EJL = '''<table><tr><th>Võistkond</th></tr>
<tr><td>1</td><td>Tallinna FCI Levadia</td><td>36</td><td>28</td><td>7</td><td>1</td><td>97:29</td><td>91</td></tr>
<tr><td>2</td><td>S. Saku Sporting</td><td>7</td><td>2</td><td>1</td><td>4</td><td>29:26</td><td>7</td></tr></table>'''

DP = '''<table><tr><td>1</td><td>Tallinna Ülikool</td><td>18</td><td>6</td><td>6</td><td>0</td><td>18</td><td>2</td><td>506</td><td>413</td></tr>
<tr><td>2</td><td>E-Lux Tallinn</td><td>1</td><td>7</td><td>0</td><td>7</td><td>3</td><td>21</td><td>465</td><td>577</td></tr></table><div>Home Team</div><td>Foo</td><td>1</td>'''


class AuditTest(unittest.TestCase):
    def test_reads_ejl_table_and_strips_futsal_prefix(self):
        t = ta.tabel_lehelt(EJL)
        self.assertEqual(t["Tallinna FCI Levadia"], (36, 28, 7, 1, 97, 29, 91))
        self.assertEqual(t["Saku Sporting"], (7, 2, 1, 4, 29, 26, 7))

    def test_reads_dataproject_standings(self):
        t = ta.tabel_dataproject(DP)
        self.assertEqual(t["Tallinna Ülikool"], (6, 6, 0, 18, 2))
        self.assertEqual(t["E-Lux Tallinn"], (7, 0, 7, 3, 21))

    def test_football_table_from_results(self):
        ev = [{"league": "L", "away": "B", "home": "A", "result": "2-1"}, {"league": "L", "away": "A", "home": "B", "result": "0-0"},
              {"league": "L", "away": "B", "home": "A", "result": ""}, {"league": "X", "away": "B", "home": "A", "result": "5-0"}]
        r = ta.arvuta(ev, "L")
        self.assertEqual(r["A"], [2, 1, 1, 0, 2, 1, 4])     # mänge, V, X, K, väravad, vastu, punkte
        self.assertEqual(r["B"], [2, 0, 1, 1, 1, 2, 1])

    def test_volleyball_table_from_results(self):
        ev = [{"league": "L", "home": "A", "away": "B", "result": "3-1"}, {"league": "L", "home": "B", "away": "A", "result": "2-3"}]
        r = ta.arvuta_vorkpall(ev, "L")
        self.assertEqual(r["A"], [2, 2, 0, 6, 3])           # mänge, V, K, setid võidetud, kaotatud
        self.assertEqual(r["B"], [2, 0, 2, 3, 6])


if __name__ == "__main__":
    unittest.main()
