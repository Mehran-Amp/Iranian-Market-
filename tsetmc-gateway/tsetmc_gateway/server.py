"""Read-only JSON HTTP API (standard library only)."""
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .schedule import is_active_window

log = logging.getLogger("tsetmc.api")


class Api:
    """Routing and response building, separate from sockets so it is easy to test."""

    def __init__(self, store, cfg, active=is_active_window):
        self.store, self.cfg, self.active = store, cfg, active

    # ---- helpers ------------------------------------------------------
    def _is_stale(self) -> bool:
        age = self.store.age()
        if age is None:
            return True
        limit = self.cfg.stale_after if self.active() else self.cfg.idle_interval * 3
        return age > limit

    def _meta(self) -> dict:
        age = self.store.age()
        last_ok = self.store.last_ok
        return {
            "unit": "IRR",  # prices are in Rial; divide by 10 for Toman
            "seq": self.store.seq,
            "stale": self._is_stale(),
            "age_seconds": None if age is None else round(age, 1),
            "updated_at": (datetime.fromtimestamp(last_ok, timezone.utc).isoformat()
                           if last_ok else None),
        }

    def _ok(self, data, extra=None):
        body = {"meta": self._meta(), "data": data}
        if extra:
            body.update(extra)
        return 200, body

    @staticmethod
    def _err(status, message):
        return status, {"error": message}

    @staticmethod
    def _one(params, name, default=""):
        v = params.get(name)
        return v[0] if v else default

    @staticmethod
    def _int(params, name, default, lo, hi):
        try:
            v = int(Api._one(params, name, default))
        except ValueError:
            v = default
        return max(lo, min(hi, v))

    # ---- routes -------------------------------------------------------
    def handle(self, path: str, params: dict):
        s = self.store
        if path == "/health":
            return 200, {
                "status": "ok" if s.ready and not self._is_stale() else "degraded",
                "version": __version__,
                "ready": s.ready,
                "stale": self._is_stale(),
                "age_seconds": None if s.age() is None else round(s.age(), 1),
                "instruments": len(s.by_id),
                "seq": s.seq,
                "refid": s.refid,
                "h": s.h,
                "active_window": self.active(),
                "stats": s.stats,
            }
        if not s.ready:
            return self._err(503, "market data not loaded yet; try again shortly")

        if path == "/v1/symbols":
            q = self._one(params, "q")
            if not q:
                return self._err(400, "missing query parameter q")
            limit = self._int(params, "limit", 20, 1, 100)
            traded = self._one(params, "traded") in ("1", "true")
            return self._ok(s.search(q, limit, traded))

        if path == "/v1/market":
            traded = self._one(params, "traded") in ("1", "true")
            return self._ok(s.all_quotes(traded))

        if path == "/v1/changes":
            since = self._int(params, "since", 0, 0, 2**62)
            if since < s.init_seq:
                since = 0  # client is older than the last full reload: send everything
            return self._ok(s.changes_since(since))

        if path == "/v1/quotes":
            keys = [k for k in self._one(params, "symbols").split(",") if k.strip()]
            keys += [k for k in self._one(params, "ids").split(",") if k.strip()]
            if not keys:
                return self._err(400, "give symbols=a,b,c or ids=1,2,3")
            if len(keys) > 200:
                return self._err(400, "at most 200 symbols per request")
            found, missing = [], []
            for k in keys:
                inst = s.resolve(k)
                (found.append(s.quote(inst)) if inst else missing.append(k))
            return self._ok(found, {"missing": missing})

        for prefix, kind in (("/v1/quote/", "quote"), ("/v1/orderbook/", "book")):
            if path.startswith(prefix):
                key = path[len(prefix):]
                inst = s.resolve(key)
                if inst is None:
                    return self._err(404, f"unknown symbol: {key}")
                if kind == "quote":
                    return self._ok(s.quote(inst))
                return self._ok(s.orderbook(inst), {"id": inst.id, "ticker": inst.ticker})

        return self._err(404, "not found")


def make_server(cfg, store, api: Api | None = None) -> ThreadingHTTPServer:
    api = api or Api(store, cfg)

    class Handler(BaseHTTPRequestHandler):
        server_version = "tsetmc-gateway/" + __version__

        def _send(self, status, body):
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            url = urlparse(self.path)
            path = unquote(url.path)
            if cfg.api_key and path != "/health":
                given = self.headers.get("X-API-Key", "")
                if not hmac.compare_digest(given.encode(), cfg.api_key.encode()):
                    return self._send(401, {"error": "missing or wrong X-API-Key"})
            try:
                status, body = api.handle(path.rstrip("/") or "/", parse_qs(url.query))
            except Exception:  # never leak a traceback to clients
                log.exception("unhandled error for %s", self.path)
                status, body = 500, {"error": "internal error"}
            self._send(status, body)

        def log_message(self, fmt, *args):
            log.debug("%s - %s", self.address_string(), fmt % args)

    return ThreadingHTTPServer((cfg.host, cfg.port), Handler)
