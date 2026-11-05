"""Turns stored instruments into the public JSON quote shape."""
from .models import Instrument, OrderLevel


def num(x):
    """Floats that are whole numbers become ints (limits arrive as '1434.00')."""
    if isinstance(x, float) and x == int(x):
        return int(x)
    return x


def fmt_time(t: int):
    if not t:
        return None
    s = f"{t:06d}"
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"


def _change(price: int, yesterday: int):
    if price <= 0 or yesterday <= 0:
        return None, None
    diff = price - yesterday
    return diff, round(diff * 100.0 / yesterday, 2)


def _side(price: int, volume: int, orders: int):
    if price <= 0:
        return None
    return {"price": price, "volume": volume, "orders": orders}


def detect_queue(inst: Instrument, book: dict):
    """'buy' / 'sell' / None. Heuristic on level 1 of the order book.

    Buy queue: best bid sits at the upper price limit and nobody sells at that
    price. Sell queue is the mirror image at the lower limit.
    """
    lvl = book.get(1)
    up, lo = inst.upper_limit, inst.lower_limit
    if lvl is None or up <= 0 or lo <= 0 or up <= lo:
        return None
    if (lvl.buy_price >= up and lvl.buy_volume > 0 and
            (lvl.sell_price == 0 or lvl.sell_volume == 0 or lvl.sell_price > up)):
        return "buy"
    if (lvl.sell_price > 0 and lvl.sell_price <= lo and lvl.sell_volume > 0 and
            (lvl.buy_price == 0 or lvl.buy_volume == 0 or lvl.buy_price < lo)):
        return "sell"
    return None


def build_quote(inst: Instrument, book: dict | None) -> dict:
    book = book or {}
    lvl1: OrderLevel | None = book.get(1)
    lc, lcp = _change(inst.last, inst.yesterday)
    cc, ccp = _change(inst.close, inst.yesterday)
    return {
        "id": inst.id,
        "isin": inst.isin,
        "ticker": inst.ticker,
        "name": inst.name,
        "last": inst.last,
        "close": inst.close,
        "first": inst.first,
        "low": inst.low,
        "high": inst.high,
        "yesterday": inst.yesterday,
        "last_change": lc,
        "last_change_pct": lcp,
        "close_change": cc,
        "close_change_pct": ccp,
        "trades": inst.trades,
        "volume": inst.volume,
        "value": inst.value,
        "traded": inst.trades > 0,
        "upper_limit": num(inst.upper_limit),
        "lower_limit": num(inst.lower_limit),
        "best_bid": _side(lvl1.buy_price, lvl1.buy_volume, lvl1.buy_orders) if lvl1 else None,
        "best_ask": _side(lvl1.sell_price, lvl1.sell_volume, lvl1.sell_orders) if lvl1 else None,
        "queue": detect_queue(inst, book),
        "eps": inst.eps,
        "nav": num(inst.nav) if inst.nav is not None else None,
        "update_time": fmt_time(inst.time),
        "rev": inst.rev,
    }


def build_book(book: dict) -> list:
    out = []
    for level in sorted(book):
        b = book[level]
        out.append({
            "level": level,
            "buy": {"price": b.buy_price, "volume": b.buy_volume, "orders": b.buy_orders},
            "sell": {"price": b.sell_price, "volume": b.sell_volume, "orders": b.sell_orders},
        })
    return out
