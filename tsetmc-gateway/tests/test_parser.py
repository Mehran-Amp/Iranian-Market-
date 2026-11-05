import unittest

from tsetmc_gateway.parser import ParseError, parse_init, parse_plus
from tests.helpers import load


class InitParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = parse_init(load("init_sample.txt"))
        cls.by_ticker = {i.ticker: i for i in cls.data.instruments}

    def test_counts_and_cursor(self):
        self.assertEqual(len(self.data.instruments), 7)
        self.assertEqual(self.data.refid, 16375067522)
        self.assertEqual(self.data.bad_rows, 0)

    def test_bank_mellat_fields(self):
        i = self.by_ticker["\u0648\u0628\u0645\u0644\u062a"]
        self.assertEqual(i.id, "778253364357513")
        self.assertEqual(i.isin, "IRO1BMLT0001")
        self.assertEqual((i.first, i.close, i.last), (1420, 1424, 1434))
        self.assertEqual((i.low, i.high, i.yesterday), (1395, 1434, 1393))
        self.assertEqual((i.trades, i.volume, i.value), (17409, 3516841504, 5007667846820))
        self.assertEqual((i.upper_limit, i.lower_limit), (1434.0, 1352.0))
        self.assertEqual(i.eps, 602)
        self.assertEqual(i.time, 123000)

    def test_letters_are_persian(self):
        i = self.by_ticker["\u0648\u0628\u0645\u0644\u062a"]
        self.assertNotIn("\u0643", i.name)
        self.assertNotIn("\u064a", i.name)

    def test_missing_eps_and_nav(self):
        i = self.by_ticker["\u0636\u0647\u0631\u0645" + "8024"]
        self.assertIsNone(i.eps)
        self.assertIsNone(i.nav)
        gold = self.by_ticker["\u06af\u0644\u062f\u0627"]
        self.assertEqual(gold.nav, 22944.0)

    def test_order_book(self):
        gold = self.by_ticker["\u06af\u0644\u062f\u0627"]
        levels = {b.level: b.data for b in self.data.book if b.id == gold.id}
        self.assertEqual(sorted(levels), [1, 2, 3, 4, 5])
        l1 = levels[1]
        self.assertEqual((l1.buy_orders, l1.sell_orders), (2, 1))
        self.assertEqual((l1.buy_price, l1.sell_price), (22476, 22477))
        self.assertEqual((l1.buy_volume, l1.sell_volume), (156389, 200000))

    def test_rejects_garbage(self):
        with self.assertRaises(ParseError):
            parse_init("<html>blocked</html>")
        with self.assertRaises(ParseError):
            parse_init("a@b@c@d@e")

    def test_format_change_is_detected(self):
        # 600 rows, 10 of them with an extra field: more than 1% -> the format changed.
        base = load("init_sample.txt").split("@")[2].split(";")[0].split(",")
        rows = []
        for n in range(600):
            f = list(base)
            f[0] = str(1000 + n)
            if n < 10:
                f.append("extra")
            rows.append(",".join(f))
        text = "1,2,3@@" + ";".join(rows) + "@@16375067522"
        with self.assertRaises(ParseError):
            parse_init(text)

    def test_few_bad_rows_are_tolerated(self):
        base = load("init_sample.txt").split("@")[2].split(";")[0].split(",")
        good, bad = list(base), list(base) + ["extra"]
        bad[0] = "999"
        text = "1,2,3@@" + ";".join([",".join(good), ",".join(bad)]) + "@@16375067522"
        d = parse_init(text)
        self.assertEqual((len(d.instruments), d.bad_rows), (1, 1))


class PlusParserTests(unittest.TestCase):
    def test_real_sample(self):
        d = parse_plus(load("plus_sample.txt"))
        self.assertEqual(d.refid, 16375067522)
        self.assertEqual(len(d.prices), 1)
        p = d.prices[0]
        self.assertEqual(p.id, "50264175787486822")
        self.assertEqual((p.time, p.first, p.close, p.last), (181815, 10139, 10148, 10150))
        self.assertEqual((p.trades, p.volume, p.value), (126, 2886169, 29288922743))
        self.assertEqual((p.low, p.high), (10139, 10200))
        self.assertEqual(len(d.book), 9)
        self.assertEqual(d.bad_rows, 0)

    def test_empty_delta_is_valid(self):
        d = parse_plus("1,2,3@@@@16375067600")
        self.assertEqual((d.prices, d.book, d.refid), ([], [], 16375067600))

    def test_bad_rows_are_counted_not_fatal(self):
        d = parse_plus("1,2,3@@5,1,2@1,2,3@16375067600")
        self.assertEqual(d.bad_rows, 2)

    def test_bad_cursor(self):
        with self.assertRaises(ParseError):
            parse_plus("1,2,3@@@@oops")


if __name__ == "__main__":
    unittest.main()
