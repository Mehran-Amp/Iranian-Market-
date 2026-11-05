import unittest

from tsetmc_gateway.normalize import fix_letters, normalize


class NormalizeTests(unittest.TestCase):
    def test_arabic_letters_match_persian(self):
        self.assertEqual(normalize("\u0627\u064a\u0631\u0627\u0646\u200c \u062e\u0648\u062f\u0631\u0648"),
                         normalize("\u0627\u06cc\u0631\u0627\u0646 \u062e\u0648\u062f\u0631\u0648"))

    def test_kaf_and_digits(self):
        self.assertEqual(normalize("\u0645\u0628\u0627\u0631\u0643\u0647"), normalize("\u0645\u0628\u0627\u0631\u06a9\u0647"))
        self.assertEqual(normalize("\u0641\u0648\u0644\u0627\u062f\u06f3"), "\u0641\u0648\u0644\u0627\u062f3")
        self.assertEqual(normalize("\u0641\u0648\u0644\u0627\u062f\u0663"), "\u0641\u0648\u0644\u0627\u062f3")

    def test_whitespace_and_case(self):
        self.assertEqual(normalize("  IRO1 BMLT0001 "), "iro1 bmlt0001")

    def test_fix_letters_keeps_zwnj(self):
        self.assertEqual(fix_letters("\u0627\u064a\u0631\u0627\u0646\u200c"), "\u0627\u06cc\u0631\u0627\u0646\u200c")


if __name__ == "__main__":
    unittest.main()
