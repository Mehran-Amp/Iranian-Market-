# API

All responses are JSON (UTF-8). Send `X-API-Key: <key>` if `TSETMC_API_KEY` is set
(`/health` is always open).

Envelope: `{"meta": {...}, "data": ...}`

`meta`: `unit` ("IRR"), `seq` (change counter), `stale` (bool), `age_seconds` (since the last
successful TSETMC fetch), `updated_at` (UTC ISO time).
Errors: `{"error": "..."}` with status 400, 401, 404, 503 (data not loaded yet) or 500.

## Quote object

| Field | Meaning |
|---|---|
| `id`, `isin`, `ticker`, `name` | Identity. Use `id` as the stable key; tickers can change. |
| `last`, `close`, `first`, `low`, `high`, `yesterday` | Prices in Rial |
| `last_change`, `last_change_pct`, `close_change`, `close_change_pct` | vs. `yesterday`; `null` if there is no price |
| `trades`, `volume`, `value`, `traded` | Activity; `traded` = `trades > 0` |
| `upper_limit`, `lower_limit` | Daily price limits |
| `best_bid`, `best_ask` | `{price, volume, orders}` or `null` |
| `queue` | `"buy"`, `"sell"` or `null` |
| `eps`, `nav` | When available |
| `update_time` | `HH:MM:SS` Tehran time of the instrument's last update |
| `rev` | `seq` value when this instrument last changed |

## Endpoints

- `GET /health` -> `status` (`ok` or `degraded`), `ready`, `stale`, `age_seconds`, `instruments`, `seq`, `refid`, `h`, `active_window`, `stats`.
- `GET /v1/symbols?q=TEXT&limit=20&traded=1` -> quotes ranked: exact ticker, ticker prefix, ticker contains, name prefix, name contains. `q` accepts Arabic or Persian letters and digits.
- `GET /v1/quote/{ticker|id|ISIN}` -> one quote.
- `GET /v1/quotes?symbols=a,b&ids=1,2` -> `data` (found) and top-level `missing` (not found). Max 200.
- `GET /v1/orderbook/{ticker|id}` -> `data`: levels 1-5 with `buy` and `sell` `{price, volume, orders}`.
- `GET /v1/market?traded=1` -> every quote (about 2 MB for the full market).
- `GET /v1/changes?since=N` -> quotes with `rev > N`. Start with `since=0`, then pass the `meta.seq` you got last time. If you are older than the last full reload you get everything again.
