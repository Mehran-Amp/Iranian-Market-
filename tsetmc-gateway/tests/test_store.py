import unittest

from tsetmc_gateway.models import Instrument, OrderLevel
from tsetmc_gateway.parser import parse_init, parse_plus
from tsetmc_gateway.quotes import detect_queue
from tsetmc_gateway.store import MarketStore
from tests.helpers import load

TARANJ = "\u062a\u0631\u0646\u062c \u062b\u0627\u0628\u062a"
GOLD = "\u06af\u0644\u062f\u0627"


def loaded_store():
    s = MarketStore()
    s.apply_init(parse_init(load("init_sample.txt")))
    s.mark_ok()
    return s


class StoreTests(unittest.TestCase):
    def test_init_sets_state(self):
        s = loaded_store()
        self.assertTrue(s.ready)
        self.assertEqual(len(s.by_id), 7)
        self.assertEqual(s.refid, 16375067522)
        self.assertEqual(s.h, 181815)

    def test_resolve_any_spelling(self):
        s = loaded_store()
        self.assertEqual(s.resolve("\u0648\u0628\u0645\u0644\u062a").ticker, "\u0648\u0628\u0645\u0644\u062a")
        self.assertEqual(s.resolve("IRO1BMLT0001").id, "778253364357513")
        self.assertEqual(s.resolve("778253364357513").isin, "IRO1BMLT0001")
        self.assertEqual(s.resolve("\u0636\u0647\u0631\u0645\u06f8\u06f0\u06f2\u06f4").id, "56954662775448971")
        self.assertIsNone(s.resolve("nope"))

    def test_search_ranking(self):
        s = loaded_store()
        res = s.search("\u0641\u0648\u0644\u0627\u062f")
        self.assertEqual(res[0]["ticker"], "\u0641\u0648\u0644\u0627\u062f")  # exact first
        self.assertIn("\u0641\u0648\u0644\u0627\u062f3", [r["ticker"] for r in res])
        self.assertEqual(s.search("\u0627\u064a\u0631\u0627\u0646 \u062e\u0648\u062f\u0631\u0648")[0]["ticker"], "\u062e\u0648\u062f\u0631\u0648")
        self.assertEqual(s.search("zzzz"), [])

    def test_change_math_matches_tsetmc_export(self):
        q = loaded_store().quote(loaded_store().resolve("\u0636\u0647\u0631\u0645\u06f8\u06f0\u06f2\u06f4"))
        # values taken from the real MarketWatch.xls export
        self.assertEqual((q["last_change"], q["last_change_pct"]), (2715, 6.27))
        self.assertEqual((q["close_change"], q["close_change_pct"]), (2186, 5.05))

    def test_plus_updates_and_bumps_seq(self):
        s = loaded_store()
        before = s.seq
        text = ("1,2,3@@" + TID + ",190000,10100,10110,10200,130,2900000,29300000000,10100,10250"
                "@" + TID + ",1,1,1,10190,10200,500,600@16375067600")
        unknown = s.apply_plus(parse_plus(text))
        self.assertEqual(unknown, 0)
        self.assertEqual(s.seq, before + 1)
        q = s.quote(s.resolve(TARANJ))
        self.assertEqual((q["first"], q["close"], q["last"]), (10100, 10110, 10200))
        self.assertEqual((q["trades"], q["high"], q["update_time"]), (130, 10250, "19:00:00"))
        self.assertEqual(q["best_bid"]["price"], 10190)
        self.assertEqual(s.refid, 16375067600)
        self.assertEqual(s.h, 190000)
        self.assertEqual([c["ticker"] for c in s.changes_since(before)], [TARANJ])

    def test_identical_delta_changes_nothing(self):
        # The real Plus sample carries the same values Init already has.
        s = loaded_store()
        before = s.seq
        s.apply_plus(parse_plus(load("plus_sample.txt")))
        s.apply_plus(parse_plus(load("plus_sample.txt")))
        self.assertEqual(s.seq, before)
        self.assertEqual(s.changes_since(before), [])

    def test_unknown_ids_are_counted(self):
        s = loaded_store()
        self.assertGreater(s.apply_plus(parse_plus(load("plus_sample.txt"))), 0)

    def test_staleness_clock(self):
        t = [1000.0]
        s = MarketStore(clock=lambda: t[0])
        self.assertIsNone(s.age())
        s.mark_ok()
        t[0] = 1030.0
        self.assertEqual(s.age(), 30.0)


TID = "50264175787486822"


def inst(**kw):
    base = dict(id="1", isin="X", ticker="T", name="N", upper_limit=110.0, lower_limit=90.0)
    base.update(kw)
    return Instrument(**base)


class QueueTests(unittest.TestCase):
    def test_buy_queue(self):
        book = {1: OrderLevel(5, 0, 110, 0, 100000, 0)}
        self.assertEqual(detect_queue(inst(), book), "buy")

    def test_buy_queue_when_asks_are_above_limit(self):
        book = {1: OrderLevel(5, 2, 110, 115, 100000, 50)}
        self.assertEqual(detect_queue(inst(), book), "buy")

    def test_not_a_queue_when_sellers_at_limit(self):
        book = {1: OrderLevel(5, 3, 110, 110, 100000, 500)}
        self.assertIsNone(detect_queue(inst(), book))

    def test_sell_queue(self):
        book = {1: OrderLevel(0, 7, 0, 90, 0, 300000)}
        self.assertEqual(detect_queue(inst(), book), "sell")

    def test_no_limits_no_queue(self):
        book = {1: OrderLevel(5, 0, 110, 0, 100000, 0)}
        self.assertIsNone(detect_queue(inst(upper_limit=0.0, lower_limit=0.0), book))
        self.assertIsNone(detect_queue(inst(), {}))


if __name__ == "__main__":
    unittest.main()
