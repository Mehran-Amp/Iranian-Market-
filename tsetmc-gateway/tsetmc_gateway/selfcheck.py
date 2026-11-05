"""One-shot live check. Run it on the machine that will host the gateway:

    python -m tsetmc_gateway.selfcheck

It downloads Init and one Plus response from TSETMC, checks that the format
still matches docs/FIELD_MAP.md and prints a few quotes. Exit code 0 = OK.
"""
import sys

from .client import http_get
from .config import Config
from .parser import ParseError, parse_init, parse_plus
from .store import MarketStore


def main() -> int:
    cfg = Config.from_env()
    store = MarketStore()
    try:
        print("Downloading Init ...")
        init = parse_init(http_get(cfg.init_url(), cfg.http_timeout, cfg.user_agent))
        store.apply_init(init)
        print(f"  instruments: {len(init.instruments)}  order-book rows: {len(init.book)}"
              f"  bad rows: {init.bad_rows}  r={init.refid}  h={store.h}")
        print("Downloading Plus ...")
        plus = parse_plus(http_get(cfg.plus_url(store.h, store.refid),
                                   cfg.http_timeout, cfg.user_agent))
        unknown = store.apply_plus(plus)
        print(f"  price rows: {len(plus.prices)}  book rows: {len(plus.book)}"
              f"  bad rows: {plus.bad_rows}  unknown ids: {unknown}  next r={plus.refid}")
    except (ParseError, OSError, RuntimeError) as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        print("If this is a network error, TSETMC may block this server's IP "
              "(common for hosts outside Iran). Try another host or a proxy.")
        return 1
    for ticker in ("\u0648\u0628\u0645\u0644\u062a", "\u0641\u0648\u0644\u0627\u062f"):
        inst = store.resolve(ticker)
        if inst:
            q = store.quote(inst)
            print(f"  {q['ticker']}: last={q['last']} close={q['close']} "
                  f"yesterday={q['yesterday']} change%={q['last_change_pct']} "
                  f"queue={q['queue']} time={q['update_time']}")
    bad = init.bad_rows + plus.bad_rows
    print("OK" if bad == 0 else f"OK with {bad} malformed rows - check docs/FIELD_MAP.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
