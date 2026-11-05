import unittest

from tsetmc_gateway.collector import Collector
from tsetmc_gateway.config import Config
from tsetmc_gateway.store import MarketStore
from tests.helpers import load

INIT = load("init_sample.txt")
PLUS_SAME = load("plus_sample.txt")  # contains ids that are not in the fixture
EMPTY_PLUS = "1,2,3@@@@16375067600"


class FakeNet:
    def __init__(self, *responses):
        self.responses, self.urls = list(responses), []

    def __call__(self, url):
        self.urls.append(url)
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r


def make(net, **cfg):
    c = Config(**cfg)
    return Collector(c, MarketStore(), net, active=lambda: True), c


class CollectorTests(unittest.TestCase):
    def test_init_then_plus_uses_cursors(self):
        net = FakeNet(INIT, EMPTY_PLUS, EMPTY_PLUS)
        col, cfg = make(net)
        self.assertEqual(col.step(), cfg.poll_interval)
        self.assertTrue(col.store.ready)
        col.step()
        self.assertTrue(net.urls[0].endswith("MarketWatchInit.aspx?h=0&r=0"))
        self.assertTrue(net.urls[1].endswith("MarketWatchPlus.aspx?h=181815&r=16375067522"))
        col.step()
        self.assertTrue(net.urls[2].endswith("h=181815&r=16375067600"))

    def test_idle_window_polls_slowly(self):
        col, cfg = make(FakeNet(INIT))
        col.active = lambda: False
        self.assertEqual(col.step(), cfg.idle_interval)

    def test_unknown_ids_trigger_resync(self):
        net = FakeNet(INIT, PLUS_SAME, INIT)
        col, _ = make(net, unknown_resync_cooldown=0)
        col.step(); col.step()
        self.assertTrue(col.force_init)
        col.step()
        self.assertTrue(net.urls[2].endswith("h=0&r=0"))
        self.assertFalse(col.force_init)

    def test_errors_back_off_and_recover(self):
        net = FakeNet(OSError("down"), INIT)
        col, cfg = make(net)
        d1 = col.step()
        self.assertEqual(col.failures, 1)
        self.assertGreater(d1, cfg.poll_interval)
        col.step()
        self.assertEqual(col.failures, 0)
        self.assertTrue(col.store.ready)
        self.assertEqual(col.store.stats["errors"], 1)

    def test_five_failures_force_full_reload(self):
        net = FakeNet(INIT, *([OSError("down")] * 5), INIT)
        col, _ = make(net)
        col.step()
        for _ in range(5):
            col.step()
        self.assertTrue(col.force_init)

    def test_garbage_response_is_an_error_not_a_crash(self):
        col, _ = make(FakeNet("<html>Access denied</html>"))
        col.step()
        self.assertFalse(col.store.ready)
        self.assertEqual(col.failures, 1)

    def test_daily_refresh(self):
        t = [0.0]
        net = FakeNet(INIT, INIT)
        c = Config(init_refresh_seconds=100)
        col = Collector(c, MarketStore(clock=lambda: t[0]), net, clock=lambda: t[0], active=lambda: True)
        col.step()
        t[0] = 500
        col.step()
        self.assertTrue(net.urls[1].endswith("h=0&r=0"))


if __name__ == "__main__":
    unittest.main()
