import json
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import quote as urlquote

from tsetmc_gateway.config import Config
from tsetmc_gateway.server import Api, make_server
from tests.test_store import loaded_store

MELLAT = "\u0648\u0628\u0645\u0644\u062a"
GOLD = "\u06af\u0644\u062f\u0627"


def api(active=True):
    return Api(loaded_store(), Config(), active=lambda: active)


class ApiTests(unittest.TestCase):
    def test_health(self):
        status, body = api().handle("/health", {})
        self.assertEqual(status, 200)
        self.assertEqual((body["status"], body["instruments"], body["ready"]), ("ok", 7, True))

    def test_not_ready_returns_503(self):
        from tsetmc_gateway.store import MarketStore
        status, _ = Api(MarketStore(), Config()).handle("/v1/market", {})
        self.assertEqual(status, 503)

    def test_quote_by_ticker_and_meta(self):
        status, body = api().handle("/v1/quote/" + MELLAT, {})
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["last"], 1434)
        self.assertEqual(body["meta"]["unit"], "IRR")
        self.assertFalse(body["meta"]["stale"])

    def test_quote_unknown_is_404(self):
        self.assertEqual(api().handle("/v1/quote/nope", {})[0], 404)

    def test_quotes_reports_missing(self):
        status, body = api().handle("/v1/quotes", {"symbols": [MELLAT + ",nope," + GOLD]})
        self.assertEqual(status, 200)
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["missing"], ["nope"])

    def test_orderbook_sorted(self):
        status, body = api().handle("/v1/orderbook/" + GOLD, {})
        self.assertEqual([l["level"] for l in body["data"]], [1, 2, 3, 4, 5])
        self.assertEqual(body["data"][0]["buy"]["price"], 22476)

    def test_symbols_requires_q(self):
        self.assertEqual(api().handle("/v1/symbols", {})[0], 400)
        status, body = api().handle("/v1/symbols", {"q": ["\u0641\u0648\u0644\u0627\u062f"], "limit": ["1"]})
        self.assertEqual(len(body["data"]), 1)

    def test_changes(self):
        a = api()
        _, body = a.handle("/v1/changes", {"since": ["0"]})
        self.assertEqual(len(body["data"]), 7)           # everything after the first Init
        seq = body["meta"]["seq"]
        _, body = a.handle("/v1/changes", {"since": [str(seq)]})
        self.assertEqual(body["data"], [])

    def test_stale_flag(self):
        a = api()
        a.store._clock = lambda: a.store.last_ok + 500
        self.assertTrue(a.handle("/v1/quote/" + MELLAT, {})[1]["meta"]["stale"])
        self.assertEqual(a.handle("/health", {})[1]["status"], "degraded")


class HttpTests(unittest.TestCase):
    def start(self, api_key=""):
        cfg = Config(host="127.0.0.1", port=0, api_key=api_key)
        server = make_server(cfg, loaded_store())
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def get(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def test_persian_path_over_http(self):
        base = self.start()
        status, body = self.get(base + "/v1/quote/" + urlquote(MELLAT))
        self.assertEqual((status, body["data"]["ticker"]), (200, MELLAT))

    def test_api_key(self):
        base = self.start(api_key="secret")
        self.get(base + "/health")  # health is always open
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.get(base + "/v1/market")
        self.assertEqual(cm.exception.code, 401)
        status, body = self.get(base + "/v1/market", {"X-API-Key": "secret"})
        self.assertEqual((status, len(body["data"])), (200, 7))


if __name__ == "__main__":
    unittest.main()
