"""Backtest command."""

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from mrmkt.backtest.strategy import StrategyRunner, build_strategy, parse_params
from mrmkt.command._shared import (
    normalize_symbol,
    normalize_tag,
    parse_cli_date,
    split_benchmark_symbol,
)


@dataclass(frozen=True)
class BacktestOutcome:
    """Everything the CLI renders, in order; the run already happened."""

    status: str  # "no_symbols" | "no_history" | "no_trades" | "done"
    benchmark_note: str | None
    benchmark_without_prices: str | None
    n_symbols: int
    start: date | None
    end_date: date
    summary: Any  # runner result, or None when the run produced nothing to report


class RunBacktest:
    """Backtest a strategy over stored prices with vectorbt."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(
        self,
        symbols: list[str] | None,
        all_symbols: bool,
        tags: list[str] | None,
        from_date: str | None,
        to_date: str | None,
        strategy_name: str,
        params_text: str | None,
        benchmark: str,
        size_pct: float,
        stop: float,
        fees: float,
        chunk_size: int,
    ) -> BacktestOutcome:
        selector_count = sum((bool(symbols), all_symbols, bool(tags)))
        if selector_count != 1:
            raise ValueError("provide symbols, --all, or --tag")
        if not 0 < size_pct <= 100:
            raise ValueError("size_pct must be between 0 and 100")
        if not 0 < stop < 1:
            raise ValueError("stop must be between 0 and 1")
        if fees < 0:
            raise ValueError("fees must be >= 0")
        if chunk_size < 1:
            raise ValueError("chunk-size must be at least 1")

        today = self.clock.today()
        try:
            start_date = parse_cli_date(from_date, today) if from_date is not None else None
            end_date = parse_cli_date(to_date, today) if to_date is not None else today
        except ValueError as error:
            raise ValueError("dates must be ISO dates, now, or durations such as 180d") from error
        if start_date is not None and start_date > end_date:
            raise ValueError("--from must be on or before --to")

        strategy = build_strategy(strategy_name, parse_params(params_text))

        try:
            if tags:
                selected = sorted(
                    {s for tag in tags for s in self.repository.get_symbols_by_tag(normalize_tag(tag))}
                )
            elif all_symbols:
                selected = sorted({ticker.ticker for ticker in self.repository.get_tickers()})
            else:
                selected = [normalize_symbol(symbol) for symbol in (symbols or [])]
            benchmark_symbol = normalize_symbol(benchmark) if benchmark and benchmark.strip() else ""
        except ValueError as error:
            # Tag/symbol normalization failures surface through the generic
            # failure path like before.
            raise RuntimeError(str(error)) from error
        if not selected:
            return BacktestOutcome(
                status="no_symbols",
                benchmark_note=None,
                benchmark_without_prices=None,
                n_symbols=0,
                start=None,
                end_date=end_date,
                summary=None,
            )
        selected, benchmark_note = split_benchmark_symbol(selected, benchmark_symbol)
        benchmark_series: pd.Series | None = None
        benchmark_without_prices: str | None = None
        if benchmark_symbol:
            bench_bars = list(
                self.repository.list_prices_for_symbols(
                    [benchmark_symbol], date.min, end_date
                )
            )
            if bench_bars:
                bench_index = pd.DatetimeIndex([price.date for price in bench_bars])
                benchmark_series = pd.Series(
                    [price.close for price in bench_bars], index=bench_index
                ).sort_index()
            else:
                benchmark_without_prices = benchmark_symbol

        chunks = []
        union_idx: pd.DatetimeIndex = pd.DatetimeIndex([])
        for offset in range(0, len(selected), chunk_size):
            closes, highs, lows = {}, {}, {}
            bars_by_symbol: dict = {}
            for price in self.repository.list_prices_for_symbols(
                selected[offset : offset + chunk_size], date.min, end_date
            ):
                bars_by_symbol.setdefault(price.symbol, []).append(price)
            for symbol, bars in bars_by_symbol.items():
                if len(bars) < 360:
                    continue
                index = pd.DatetimeIndex([price.date for price in bars])
                closes[symbol] = pd.Series([price.close for price in bars], index=index)
                highs[symbol] = pd.Series([price.high for price in bars], index=index)
                lows[symbol] = pd.Series([price.low for price in bars], index=index)
            if not closes:
                continue
            chunk_close = pd.DataFrame(closes).sort_index()
            chunks.append(
                (
                    chunk_close,
                    pd.DataFrame(highs).sort_index().reindex_like(chunk_close),
                    pd.DataFrame(lows).sort_index().reindex_like(chunk_close),
                )
            )
            union_idx = pd.DatetimeIndex(union_idx.union(chunk_close.index))
        if not chunks:
            return BacktestOutcome(
                status="no_history",
                benchmark_note=benchmark_note,
                benchmark_without_prices=benchmark_without_prices,
                n_symbols=0,
                start=None,
                end_date=end_date,
                summary=None,
            )
        n_symbols = sum(frame[0].shape[1] for frame in chunks)

        runner = StrategyRunner(size_pct=size_pct, stop=stop, fees=fees)
        start: date = start_date if start_date is not None else list(union_idx)[300].date()
        summary = runner.run_chunked(
            strategy, chunks, start=start, benchmark=benchmark_series
        )
        return BacktestOutcome(
            status="no_trades" if summary.n_trades == 0 else "done",
            benchmark_note=benchmark_note,
            benchmark_without_prices=benchmark_without_prices,
            n_symbols=n_symbols,
            start=start,
            end_date=end_date,
            summary=summary,
        )
