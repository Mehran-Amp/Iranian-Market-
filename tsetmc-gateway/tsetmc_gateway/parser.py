"""Parsers for MarketWatchInit.aspx and MarketWatchPlus.aspx.

Both responses have 5 parts separated by '@':
  1 market numbers | 2 market summary (Init only) | 3 rows | 4 order book | 5 cursor (r)
See docs/FIELD_MAP.md for the field tables.
"""
from .models import (BookUpdate, Instrument, InitData, OrderLevel, PlusData,
                     PriceUpdate)
from .normalize import fix_letters

INSTRUMENT_FIELDS = 26
PRICE_ROW_FIELDS = 10
BOOK_ROW_FIELDS = 8
MAX_BOOK_LEVEL = 10


class ParseError(ValueError):
    """The response does not look like a TSETMC Market Watch response."""


def to_int(s: str, default: int = 0) -> int:
    s = s.strip()
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return default


def to_int_or_none(s: str):
    s = s.strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def to_float(s: str, default: float = 0.0) -> float:
    s = s.strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def to_float_or_none(s: str):
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def split_parts(text: str) -> list:
    parts = text.lstrip("\ufeff").strip().split("@")
    if len(parts) != 5:
        raise ParseError(f"expected 5 parts separated by '@', got {len(parts)}")
    return parts


def _parse_cursor(part: str) -> int:
    part = part.strip()
    if not part.isdigit():
        raise ParseError(f"cursor part is not a number: {part[:40]!r}")
    return int(part)


def _parse_book(part: str):
    rows, bad = [], 0
    for raw in part.split(";"):
        if not raw:
            continue
        f = raw.split(",")
        if len(f) != BOOK_ROW_FIELDS:
            bad += 1
            continue
        level = to_int(f[1])
        if not 1 <= level <= MAX_BOOK_LEVEL:
            bad += 1
            continue
        rows.append(BookUpdate(f[0], level, OrderLevel(
            buy_orders=to_int(f[2]), sell_orders=to_int(f[3]),
            buy_price=to_int(f[4]), sell_price=to_int(f[5]),
            buy_volume=to_int(f[6]), sell_volume=to_int(f[7]))))
    return rows, bad


def _parse_instrument(f: list) -> Instrument:
    return Instrument(
        id=f[0], isin=f[1].strip(),
        ticker=fix_letters(f[2]).strip(), name=fix_letters(f[3]).strip(),
        time=to_int(f[4]), first=to_int(f[5]), close=to_int(f[6]),
        last=to_int(f[7]), trades=to_int(f[8]), volume=to_int(f[9]),
        value=to_int(f[10]), low=to_int(f[11]), high=to_int(f[12]),
        yesterday=to_int(f[13]), eps=to_int_or_none(f[14]),
        upper_limit=to_float(f[19]), lower_limit=to_float(f[20]),
        shares=to_int(f[21]), nav=to_float_or_none(f[23]),
    )


def parse_init(text: str) -> InitData:
    parts = split_parts(text)
    instruments, bad = [], 0
    for raw in parts[2].split(";"):
        if not raw:
            continue
        f = raw.split(",")
        if len(f) != INSTRUMENT_FIELDS or not f[0].isdigit():
            bad += 1
            continue
        instruments.append(_parse_instrument(f))
    if not instruments:
        raise ParseError("no instruments found in Init response")
    if bad > max(5, len(instruments) // 100):
        raise ParseError(f"{bad} instrument rows have an unexpected field count; "
                         "the TSETMC format may have changed")
    book, bad_book = _parse_book(parts[3])
    return InitData(parts[0], parts[1], instruments, book,
                    _parse_cursor(parts[4]), bad + bad_book)


def parse_plus(text: str) -> PlusData:
    parts = split_parts(text)
    prices, bad = [], 0
    for raw in parts[2].split(";"):
        if not raw:
            continue
        f = raw.split(",")
        if len(f) != PRICE_ROW_FIELDS or not f[0].isdigit():
            bad += 1
            continue
        prices.append(PriceUpdate(
            id=f[0], time=to_int(f[1]), first=to_int(f[2]), close=to_int(f[3]),
            last=to_int(f[4]), trades=to_int(f[5]), volume=to_int(f[6]),
            value=to_int(f[7]), low=to_int(f[8]), high=to_int(f[9])))
    book, bad_book = _parse_book(parts[3])
    return PlusData(parts[0], prices, book, _parse_cursor(parts[4]), bad + bad_book)
