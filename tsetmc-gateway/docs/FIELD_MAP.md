# Field map

Source: `https://old.tsetmc.com/tsev2/data/MarketWatchInit.aspx?h=0&r=0` and
`.../MarketWatchPlus.aspx?h=<h>&r=<r>`. Plain text. Verified on a capture dated 1405/08/13
(3,680 instruments, 17,183 order-book rows) against a Market Watch Excel export of the same day.

Both responses have **5 parts separated by `@`**; rows inside a part are separated by `;`,
fields by `,`.

| Part | Init | Plus |
|---|---|---|
| 1 | Three market-level numbers (ignored) | same (ignored) |
| 2 | Market summary line (date/time, index, totals; ignored) | empty |
| 3 | Instrument rows (26 fields) | Changed price rows (10 fields) |
| 4 | Order-book rows (8 fields) | Changed order-book rows (8 fields) |
| 5 | `r` cursor | next `r` cursor |

## Init instrument row (26 fields)

| # | Field | Status |
|---|---|---|
| 0 | Instrument ID (64-bit, keep as text) | verified |
| 1 | ISIN | verified |
| 2 | Ticker | verified |
| 3 | Name | verified |
| 4 | Last update time, HHMMSS Tehran | verified |
| 5 | First price | verified (all 2,067 export rows) |
| 6 | Closing price (weighted average, "پایانی") | verified |
| 7 | Last trade price ("آخرین") | verified |
| 8 | Number of trades | verified |
| 9 | Volume | verified |
| 10 | Value traded | verified |
| 11 | Day low | verified |
| 12 | Day high | verified |
| 13 | Yesterday's closing price | verified |
| 14 | EPS (may be empty) | verified |
| 15-18 | unknown | not used |
| 19 | Upper price limit | verified on samples (yesterday +3% / +10%) |
| 20 | Lower price limit | verified on samples |
| 21 | Shares / units outstanding | likely |
| 22 | Group or sector code | unknown, not used |
| 23 | NAV for funds (often empty) | likely |
| 24 | unknown | not used |
| 25 | Status code (`1A`, `N1`, `QS`, `3A` ...) | unknown meaning, not used |

## Plus price row (10 fields)

`id, time, first, close, last, trades, volume, value, low, high`

Order is **first, close, last** (not last, close, first). Verified: instrument
`50264175787486822` in a Plus row equals its Init row. Plus rows carry no yesterday price and
no limits; those come from Init.

## Order-book row (8 fields, Init and Plus)

`id, level(1-5), buy orders, sell orders, buy price, sell price, buy volume, sell volume`

Level 1 matched the export's best buy/sell columns for all 2,067 rows. A side with price 0 is empty.

## Derived values

- `last_change = last - yesterday`, `last_change_pct = change / yesterday * 100` (2 decimals);
  same for `close`. Matches the export (for example 46000 vs 43285 gives 2715 and 6.27%).
- **Queue** (heuristic, level 1 only, needs `upper > lower > 0`):
  buy queue = best bid >= upper limit with volume, and no sell volume at or below the limit;
  sell queue = mirror image at the lower limit.
  On the real capture it flags 277 buy and 102 sell queues. Compare with the TSETMC page before relying on it.

## Not verified (check before depending on it)

- Whether the server ever sends Plus rows with more than one update per instrument in a response.
- The exact semantics of `h` (the gateway sends the newest update time it has seen, as the web page does).
- Fields 15-18, 22, 24, 25 and Init part 2.
- Behavior around holidays and trading halts.

If TSETMC changes the format, `/health` shows `stats.bad_rows` or `stats.errors` increasing.
Update `tsetmc_gateway/parser.py` and this file together.
