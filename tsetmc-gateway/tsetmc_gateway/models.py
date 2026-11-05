from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class OrderLevel:
    buy_orders: int = 0
    sell_orders: int = 0
    buy_price: int = 0
    sell_price: int = 0
    buy_volume: int = 0
    sell_volume: int = 0


@dataclass(slots=True)
class Instrument:
    id: str
    isin: str
    ticker: str
    name: str
    time: int = 0            # HHMMSS (Tehran time) of last update
    first: int = 0
    close: int = 0           # TSETMC "closing price" (weighted average)
    last: int = 0            # last trade price
    trades: int = 0
    volume: int = 0
    value: int = 0
    low: int = 0
    high: int = 0
    yesterday: int = 0
    eps: Optional[int] = None
    upper_limit: float = 0.0
    lower_limit: float = 0.0
    shares: int = 0
    nav: Optional[float] = None
    rev: int = 0             # store sequence number of the last change


@dataclass(slots=True)
class PriceUpdate:
    id: str
    time: int
    first: int
    close: int
    last: int
    trades: int
    volume: int
    value: int
    low: int
    high: int


@dataclass(slots=True)
class BookUpdate:
    id: str
    level: int
    data: OrderLevel


@dataclass(slots=True)
class InitData:
    market_numbers: str
    summary: str
    instruments: list
    book: list
    refid: int
    bad_rows: int = 0


@dataclass(slots=True)
class PlusData:
    market_numbers: str
    prices: list
    book: list
    refid: int
    bad_rows: int = 0
