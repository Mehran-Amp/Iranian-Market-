"""Background poller: one Init call, then incremental Plus calls."""
import logging
import threading
import time

from .parser import ParseError, parse_init, parse_plus
from .schedule import is_active_window

log = logging.getLogger("tsetmc.collector")


class Collector(threading.Thread):
    """Single central poller. TSETMC sees one client no matter how many users you have."""

    def __init__(self, cfg, store, fetch, clock=time.time, active=is_active_window):
        super().__init__(name="tsetmc-collector", daemon=True)
        self.cfg, self.store, self.fetch = cfg, store, fetch
        self.clock, self.active = clock, active
        self.failures = 0          # consecutive failed requests
        self.bad_streak = 0        # consecutive responses containing malformed rows
        self.force_init = False
        self._halt = threading.Event()

    def stop(self) -> None:
        self._halt.set()

    def _need_init(self) -> bool:
        if not self.store.ready or self.force_init:
            return True
        return self.clock() - self.store.last_init > self.cfg.init_refresh_seconds

    def _interval(self) -> float:
        return self.cfg.poll_interval if self.active() else self.cfg.idle_interval

    def step(self) -> float:
        """Do one request. Returns how many seconds to wait before the next one."""
        try:
            if self._need_init():
                data = parse_init(self.fetch(self.cfg.init_url()))
                self.store.apply_init(data)
                self.force_init = False
                self.bad_streak = 0
                log.info("Init loaded: %d instruments, refid=%d",
                         len(data.instruments), data.refid)
            else:
                url = self.cfg.plus_url(self.store.h, self.store.refid)
                data = parse_plus(self.fetch(url))
                unknown = self.store.apply_plus(data)
                self.bad_streak = self.bad_streak + 1 if data.bad_rows else 0
                if self.bad_streak >= 3:
                    log.warning("3 responses in a row had malformed rows; resyncing")
                    self.force_init = True
                if unknown and self.clock() - self.store.last_init >= self.cfg.unknown_resync_cooldown:
                    log.info("%d rows for unknown instruments; resyncing", unknown)
                    self.force_init = True
            self.store.mark_ok()
            self.failures = 0
            return self._interval()
        except (ParseError, OSError, RuntimeError, ValueError) as exc:
            self.failures += 1
            self.store.mark_error(f"{type(exc).__name__}: {exc}")
            log.warning("fetch/parse failed (%d in a row): %s", self.failures, exc)
            if self.failures >= 5 and self.store.ready:
                self.force_init = True
            return min(60.0, self.cfg.poll_interval * (2 ** min(self.failures, 6)))

    def run(self) -> None:
        while not self._halt.is_set():
            delay = self.step()
            self._halt.wait(delay)
