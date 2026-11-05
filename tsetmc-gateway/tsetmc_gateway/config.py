import os
from dataclasses import dataclass


def _f(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 8080
    api_key: str = ""                  # empty = no key required
    base_url: str = "https://old.tsetmc.com/tsev2/data"
    poll_interval: float = 5.0         # seconds, during the active window
    idle_interval: float = 60.0        # seconds, outside the active window
    init_refresh_seconds: float = 6 * 3600
    stale_after: float = 60.0          # active window: data older than this is stale
    http_timeout: float = 20.0
    unknown_resync_cooldown: float = 60.0
    user_agent: str = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36")

    @classmethod
    def from_env(cls) -> "Config":
        c = cls()
        c.host = os.environ.get("TSETMC_HOST", c.host)
        c.port = int(_f("TSETMC_PORT", c.port))
        c.api_key = os.environ.get("TSETMC_API_KEY", c.api_key)
        c.base_url = os.environ.get("TSETMC_BASE_URL", c.base_url).rstrip("/")
        c.poll_interval = _f("TSETMC_POLL_INTERVAL", c.poll_interval)
        c.idle_interval = _f("TSETMC_IDLE_INTERVAL", c.idle_interval)
        c.init_refresh_seconds = _f("TSETMC_INIT_REFRESH_SECONDS", c.init_refresh_seconds)
        c.stale_after = _f("TSETMC_STALE_AFTER", c.stale_after)
        c.http_timeout = _f("TSETMC_HTTP_TIMEOUT", c.http_timeout)
        c.user_agent = os.environ.get("TSETMC_USER_AGENT", c.user_agent)
        return c

    def init_url(self) -> str:
        return f"{self.base_url}/MarketWatchInit.aspx?h=0&r=0"

    def plus_url(self, h: int, r: int) -> str:
        return f"{self.base_url}/MarketWatchPlus.aspx?h={h}&r={r}"
