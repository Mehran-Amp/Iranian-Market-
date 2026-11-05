# Integration guide (for the main app developer)

## Architecture

```
TSETMC  <--one poller-->  tsetmc-gateway  <--HTTP-->  main app (alert engine, users, push)
```

The main app never calls TSETMC. It calls this gateway, which can run on its own small server.

## Recommended flow

1. **Symbol picker:** `GET /v1/symbols?q=<text>&traded=1`. Save the chosen instrument's **`id`** (and ticker for display) in the alert. Do not key alerts by ticker.
2. **Live loop:** every 3-5 s call `GET /v1/changes?since=<last meta.seq>`. For each returned quote, evaluate only the alerts that watch that `id`.
3. **Stale gate:** if `meta.stale` is `true` (or the request fails), do **not** fire alerts and show "delayed data" in the app. Resume when it is `false`.
4. **Crossings, not levels:** fire when the price moves from one side of the target to the other between two evaluations, then apply a cooldown. Otherwise one threshold fires every poll.
5. **Which price:** let the user choose `last` (last trade) or `close` (weighted closing price, which differs from `last`). Default to `last`.
6. **Queue alerts:** use `queue` (`"buy"`/`"sell"`) transitions: `null -> "buy"` and `"buy" -> null` are the useful events.
7. **Units:** Rial. Divide by 10 to show Toman. Never use floating point for prices; they are integers.
8. **Search normalization:** the gateway handles ي/ی and ك/ک and Persian/Arabic digits, so pass user text as typed.

## Operations

- Run `python -m tsetmc_gateway.selfcheck` on the target server before deploying.
- Put it behind a private network or HTTPS reverse proxy, keep `TSETMC_API_KEY` set, and bind to `127.0.0.1` unless the app is on another machine.
- Monitor `/health`: alert yourself on `status != "ok"` during trading hours, and on `stats.errors` / `stats.bad_rows` growing.
- Trading hours differ by instrument (stocks about 09:00-12:30, some funds later). The gateway polls fast on Sat-Wed 08:30-19:00 Tehran time and slowly otherwise; staleness is judged accordingly.
- Memory use is small (a few tens of MB). One instance is enough; do not run several pollers.

## Things to decide on the app side

- Holiday calendar (the gateway still polls on holidays; nothing changes).
- Whether to store history (the gateway keeps only the latest state).
- Instrument types: options, rights and bonds are included. Filter with `traded=1` or by ticker in your UI if you only want shares.
