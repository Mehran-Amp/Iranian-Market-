# TSETMC Gateway

A small, read-only service that turns the Tehran Stock Exchange **Market Watch** feed
(`old.tsetmc.com`) into a clean JSON API. Your main app calls this gateway instead of
talking to TSETMC directly.

- Covers the **whole market** (about 3,700 instruments: stocks, funds, options, rights, bonds).
- **One central poller**: TSETMC sees a single client, however many users or alerts you have.
- **No dependencies**: Python 3.10+ standard library only.
- Handles the Iranian data quirks: Arabic/Persian letters and digits, Rial prices, price
  limits, buy/sell queues, last price vs. closing price, stale-data detection.
- The gateway only serves data. **Alert rules stay in your main app**, which reads this API.

## Quick start (Windows Command Prompt)

```
py --version                       (needs 3.10 or newer)
py -m tsetmc_gateway.selfcheck     (live test: downloads data and checks the format)
set TSETMC_API_KEY=choose-a-long-secret
py -m tsetmc_gateway
```

Then open `http://127.0.0.1:8080/health` and `http://127.0.0.1:8080/v1/quote/وبملت`
(add the header `X-API-Key: <your key>` for everything except `/health`).

Linux/macOS: use `python3` and `export TSETMC_API_KEY=...`. Docker: `docker build -t tsetmc-gateway .`

> **Run `selfcheck` first, on the machine that will host the service.** TSETMC may block or
> throttle servers outside Iran. If selfcheck fails with a network error, host the gateway
> somewhere that can reach `old.tsetmc.com`, or set `HTTPS_PROXY`.

## API (details in `docs/API.md`)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Service status, staleness, counters (no API key needed) |
| `GET /v1/symbols?q=فولاد&limit=20&traded=1` | Search by ticker, name or ISIN |
| `GET /v1/quote/{ticker or id or ISIN}` | One quote |
| `GET /v1/quotes?symbols=وبملت,فولاد` | Several quotes (up to 200) |
| `GET /v1/orderbook/{ticker or id}` | Five order-book levels |
| `GET /v1/market?traded=1` | The whole market (about 2 MB) |
| `GET /v1/changes?since=<seq>` | Only instruments changed after `seq` (use this to drive alerts) |

Prices are **Rial** (`meta.unit = "IRR"`). Divide by 10 for Toman.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `TSETMC_HOST` / `TSETMC_PORT` | `127.0.0.1` / `8080` | Where the API listens |
| `TSETMC_API_KEY` | empty | If set, clients must send `X-API-Key` |
| `TSETMC_POLL_INTERVAL` | `5` | Seconds between updates in the active window |
| `TSETMC_IDLE_INTERVAL` | `60` | Seconds between updates outside it |
| `TSETMC_STALE_AFTER` | `60` | Data older than this (active window) is flagged `stale` |
| `TSETMC_INIT_REFRESH_SECONDS` | `21600` | Full reload interval (new listings, symbol changes) |
| `TSETMC_BASE_URL` | `https://old.tsetmc.com/tsev2/data` | Source URL |
| `TSETMC_HTTP_TIMEOUT` / `TSETMC_USER_AGENT` | `20` / a browser UA | HTTP settings |

## How it works

1. `MarketWatchInit.aspx` is loaded once (about 1.3 MB): every instrument, its prices, limits and order book.
2. `MarketWatchPlus.aspx?h=<time>&r=<cursor>` is polled every few seconds and returns only changed rows.
3. Any doubt (errors, unknown instruments, malformed rows, 6 hours passed) triggers a full reload.
4. Everything is merged into one in-memory table that the API reads.

## Tests

```
python -m unittest discover -s tests -t .
```

The test fixtures come from a real TSETMC capture (1405/08/13), and the field map was checked
against a real Market Watch Excel export. See `docs/FIELD_MAP.md` for what is verified and what is not.

## Notes and limits

- This uses the legacy `old.tsetmc.com` interface, which can change without notice. The parser
  fails loudly (and `/health` reports it) when field counts change.
- Check TSETMC's terms of use before commercial use. For a paid product, consider a licensed data vendor as a fallback.
- Stock prices are accurate to what TSETMC publishes. Prices are not adjusted for splits or dividends.
- The buy/sell queue flag is a heuristic on the best order-book level; see `docs/FIELD_MAP.md`.

More: `docs/INTEGRATION.md` (for the main app developer), `docs/API.md`, `docs/FIELD_MAP.md`.
