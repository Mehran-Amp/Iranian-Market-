import logging

from .client import http_get
from .collector import Collector
from .config import Config
from .server import make_server
from .store import MarketStore


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = Config.from_env()
    store = MarketStore()
    collector = Collector(
        cfg, store, lambda url: http_get(url, cfg.http_timeout, cfg.user_agent))
    collector.start()
    server = make_server(cfg, store)
    logging.info("TSETMC gateway listening on http://%s:%d", cfg.host, cfg.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        server.server_close()


if __name__ == "__main__":
    main()
