# basit testler - unittest ile yazdim

import tempfile
import unittest
from pathlib import Path

from turkgrep.replacer import Replacer
from turkgrep.searcher import Searcher


class AramaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.py").write_text("def foo():\n    TODO = 1\n", encoding="utf-8")
        (self.root / "b.txt").write_text("TODO satir\n", encoding="utf-8")
        (self.root / "skip.bin").write_bytes(b"\x00\x01")

    def tearDown(self):
        self.tmp.cleanup()

    def test_arama(self):
        sonuc = Searcher("TODO").search([self.root])
        self.assertEqual(sonuc.stats.matches, 2)

    def test_buyuk_harf(self):
        sonuc = Searcher("todo", ignore_case=True).search([self.root])
        self.assertEqual(sonuc.stats.matches, 2)

    def test_uzanti(self):
        sonuc = Searcher("TODO").search([self.root], extensions={"py"})
        self.assertEqual(sonuc.stats.matches, 1)


class DegistirmeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dosya = self.root / "kod.py"
        self.dosya.write_text("eski = 1\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_onizleme(self):
        sonuc = Replacer("eski", "yeni").replace([self.root], dry_run=True)
        self.assertEqual(len(sonuc.changes), 1)
        self.assertIn("eski", self.dosya.read_text(encoding="utf-8"))

    def test_uygula(self):
        Replacer("eski", "yeni").replace([self.root], dry_run=False)
        self.assertIn("yeni", self.dosya.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
