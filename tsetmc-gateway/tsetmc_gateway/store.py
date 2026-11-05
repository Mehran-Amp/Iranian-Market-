"""Thread-safe in-memory market state."""
import threading
import time

from .models import InitData, OrderLevel, PlusData
from .normalize import normalize
from .quotes import build_book, build_quote


class MarketStore:
    def __init__(self, clock=time.time):
        self._lock = threading.RLock()
        self._clock = clock
        self.by_id: dict = {}
        self.by_key: dict = {}      # normalized ticker -> id
        self.by_isin: dict = {}     # lowercase isin -> id
        self.search_keys: dict = {}  # id -> (norm ticker, norm name)
        self.books: dict = {}       # id -> {level: OrderLevel}
        self.seq = 0
        self.init_seq = 0
        self.refid = 0
        self.h = 0                  # latest update time seen (HHMMSS)
        self.summary = ""
        self.ready = False
        self.last_ok: float = 0.0
        self.last_init: float = 0.0
        self.stats = {"init_ok": 0, "plus_ok": 0, "bad_rows": 0,
                      "unknown_ids": 0, "errors": 0, "last_error": None}

    # ---- writes -------------------------------------------------------
    def apply_init(self, data: InitData) -> None:
        with self._lock:
            self.seq += 1
            by_id, by_key, by_isin, keys = {}, {}, {}, {}
            for inst in data.instruments:
                inst.rev = self.seq
                by_id[inst.id] = inst
                nt, nn = normalize(inst.ticker), normalize(inst.name)
                keys[inst.id] = (nt, nn)
                by_key.setdefault(nt, inst.id)
                if inst.isin:
                    by_isin.setdefault(inst.isin.lower(), inst.id)
            books = {}
            for b in data.book:
                if b.id in by_id:
                    books.setdefault(b.id, {})[b.level] = b.data
            self.by_id, self.by_key, self.by_isin = by_id, by_key, by_isin
            self.search_keys, self.books = keys, books
            self.init_seq = self.seq
            self.refid = data.refid
            self.h = max((i.time for i in data.instruments), default=0)
            self.summary = data.summary
            self.ready = True
            self.last_init = self._clock()
            self.stats["init_ok"] += 1
            self.stats["bad_rows"] += data.bad_rows

    def apply_plus(self, data: PlusData) -> int:
        """Merge a delta. Returns the number of rows for unknown instrument IDs."""
        with self._lock:
            changed, unknown = set(), 0
            for p in data.prices:
                inst = self.by_id.get(p.id)
                if inst is None:
                    unknown += 1
                    continue
                new = (p.time, p.first, p.close, p.last, p.trades,
                       p.volume, p.value, p.low, p.high)
                old = (inst.time, inst.first, inst.close, inst.last, inst.trades,
                       inst.volume, inst.value, inst.low, inst.high)
                if new != old:
                    (inst.time, inst.first, inst.close, inst.last, inst.trades,
                     inst.volume, inst.value, inst.low, inst.high) = new
                    changed.add(p.id)
                if p.time > self.h:
                    self.h = p.time
            for b in data.book:
                if b.id not in self.by_id:
                    unknown += 1
                    continue
                levels = self.books.setdefault(b.id, {})
                if levels.get(b.level) != b.data:
                    levels[b.level] = b.data
                    changed.add(b.id)
            if changed:
                self.seq += 1
                for iid in changed:
                    self.by_id[iid].rev = self.seq
            if data.refid > 0:
                self.refid = data.refid
            self.stats["plus_ok"] += 1
            self.stats["bad_rows"] += data.bad_rows
            self.stats["unknown_ids"] += unknown
            return unknown

    def mark_ok(self) -> None:
        with self._lock:
            self.last_ok = self._clock()

    def mark_error(self, message: str) -> None:
        with self._lock:
            self.stats["errors"] += 1
            self.stats["last_error"] = {"message": message[:300], "at": self._clock()}

    # ---- reads --------------------------------------------------------
    def age(self) -> float | None:
        with self._lock:
            return None if not self.last_ok else self._clock() - self.last_ok

    def resolve(self, key: str):
        """Find an instrument by numeric ID, ISIN or ticker (any Arabic/Persian spelling)."""
        key = key.strip()
        with self._lock:
            if key.isdigit() and key in self.by_id:
                return self.by_id[key]
            iid = self.by_isin.get(key.lower()) or self.by_key.get(normalize(key))
            return self.by_id.get(iid) if iid else None

    def quote(self, inst) -> dict:
        with self._lock:
            return build_quote(inst, self.books.get(inst.id))

    def orderbook(self, inst) -> list:
        with self._lock:
            return build_book(self.books.get(inst.id, {}))

    def all_quotes(self, traded_only: bool = False) -> list:
        with self._lock:
            return [build_quote(i, self.books.get(i.id)) for i in self.by_id.values()
                    if not traded_only or i.trades > 0]

    def changes_since(self, since: int) -> list:
        with self._lock:
            return [build_quote(i, self.books.get(i.id)) for i in self.by_id.values()
                    if i.rev > since]

    def search(self, query: str, limit: int = 20, traded_only: bool = False) -> list:
        nq = normalize(query)
        if not nq:
            return []
        scored = []
        with self._lock:
            for iid, (nt, nn) in self.search_keys.items():
                inst = self.by_id[iid]
                if traded_only and inst.trades <= 0:
                    continue
                if nq == nt or nq == inst.isin.lower():
                    score = 0
                elif nt.startswith(nq):
                    score = 1
                elif nq in nt:
                    score = 2
                elif nn.startswith(nq):
                    score = 3
                elif nq in nn:
                    score = 4
                else:
                    continue
                scored.append((score, -inst.trades, inst.ticker, inst))
            scored.sort(key=lambda x: x[:3])
            return [build_quote(s[3], self.books.get(s[3].id)) for s in scored[:limit]]
