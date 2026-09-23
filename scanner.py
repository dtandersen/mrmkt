"""Universe screener entry point: tag workflow over the local catalog.

Replaces the legacy hardcoded S&P list and direct postgres handle with
the supported layers: tag selection plus ``ScreenUseCase`` over the
local ticker repository (same seam the ``mrmkt screen`` CLI uses).

Usage:
    uv run scanner.py --tag sp500 --exclude-tag etf --top 20
    uv run scanner.py --tag sp500 --as-of 2026-09-22 --min-price 10
"""

import argparse
import sys
from datetime import date

sys.path.insert(0, "src")

from mrmkt.cli import create_local_ticker_repository, normalize_tag, parse_cli_date
from mrmkt.common.clock import WallClock
from mrmkt.usecase.screen import ScreenRequest, ScreenUseCase, render_csv


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", action="append", default=[], help="Include tag (repeatable)")
    parser.add_argument("--exclude-tag", action="append", default=[], help="Exclude tag (repeatable)")
    parser.add_argument("--as-of", default=None, help="Screening date (default: latest bar)")
    parser.add_argument("--mode", default="technical-only", help="Screening mode")
    parser.add_argument("--min-price", type=float, default=0.0)
    parser.add_argument("--min-dollar-vol", type=float, default=0.0)
    parser.add_argument("--min-bars", type=int, default=0)
    parser.add_argument("--max-stale-days", type=int, default=None)
    parser.add_argument("--top", type=int, default=None)
    args = parser.parse_args(argv)

    today = WallClock().today()
    as_of = parse_cli_date(args.as_of, today) if args.as_of else None
    repository, close = create_local_ticker_repository()
    try:
        result = ScreenUseCase(repository).execute(
            ScreenRequest(
                include_tags=[normalize_tag(t) for t in args.tag],
                exclude_tags=[normalize_tag(t) for t in args.exclude_tag],
                as_of=as_of if isinstance(as_of, date) else None,
                mode=args.mode,
                min_price=args.min_price,
                min_dollar_vol=args.min_dollar_vol,
                min_bars=args.min_bars,
                max_stale_days=args.max_stale_days,
                top_n=args.top,
            )
        )
    finally:
        close()
    sys.stdout.write(render_csv(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
