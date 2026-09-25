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
from mrmkt.command.base import BaseResult, Command


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


@dataclass(frozen=True)
class RunBacktestRequest:
    symbols: list[str] | None = None
    all_symbols: bool = False
    tags: list[str] | None = None
    from_date: str | None = None
    to_date: str | None = None
    strategy_name: str = "buy-red"
    params_text: str | None = None
    benchmark: str = "SPY"
    size_pct: float = 2.0
    stop: float = 0.08
    fees: float = 0.0
    chunk_size: int = 250


@dataclass
class RunBacktestResult(BaseResult[BacktestOutcome]):
    pass


class RunBacktest(Command[RunBacktestRequest, RunBacktestResult]):
    """Backtest a strategy over stored prices with vectorbt."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(self, request: RunBacktestRequest) -> RunBacktestResult:
        if sum((bool(request.symbols), request.all_symbols, bool(request.tags))) != 1:
            return RunBacktestResult.invalid_data(["provide symbols, --all, or --tag"])
        if not 0 < request.size_pct <= 100:
            return RunBacktestResult.invalid_data(
                ["size_pct must be between 0 and 100"]
            )
        if not 0 < request.stop < 1:
            return RunBacktestResult.invalid_data(["stop must be between 0 and 1"])
        if request.fees < 0:
            return RunBacktestResult.invalid_data(["fees must be >= 0"])
        if request.chunk_size < 1:
            return RunBacktestResult.invalid_data(["chunk-size must be at least 1"])

        today = self.clock.today()
        try:
            start_date = (
                parse_cli_date(request.from_date, today)
                if request.from_date is not None
                else None
            )
            end_date = (
                parse_cli_date(request.to_date, today)
                if request.to_date is not None
                else today
            )
        except ValueError:
            return RunBacktestResult.invalid_data(
                ["dates must be ISO dates, now, or durations such as 180d"]
            )
        if start_date is not None and start_date > end_date:
            return RunBacktestResult.invalid_data(["--from must be on or before --to"])

        try:
            strategy = build_strategy(
                request.strategy_name, parse_params(request.params_text)
            )
            if request.tags:
                selected = sorted(
                    {
                        s
                        for tag in request.tags
                        for s in self.repository.get_symbols_by_tag(normalize_tag(tag))
                    }
                )
            elif request.all_symbols:
                selected = sorted(
                    {ticker.ticker for ticker in self.repository.get_tickers()}
                )
            else:
                selected = [
                    normalize_symbol(symbol) for symbol in (request.symbols or [])
                ]
            benchmark_symbol = (
                normalize_symbol(request.benchmark)
                if request.benchmark and request.benchmark.strip()
                else ""
            )
        except ValueError as error:
            return RunBacktestResult.invalid_data([str(error)])
        if not selected:
            return RunBacktestResult.success(
                BacktestOutcome(
                    status="no_symbols",
                    benchmark_note=None,
                    benchmark_without_prices=None,
                    n_symbols=0,
                    start=None,
                    end_date=end_date,
                    summary=None,
                )
            )
        try:
            selected, benchmark_note = split_benchmark_symbol(
                selected, benchmark_symbol
            )
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
            for offset in range(0, len(selected), request.chunk_size):
                closes, highs, lows = {}, {}, {}
                bars_by_symbol: dict = {}
                for price in self.repository.list_prices_for_symbols(
                    selected[offset : offset + request.chunk_size], date.min, end_date
                ):
                    bars_by_symbol.setdefault(price.symbol, []).append(price)
                for symbol, bars in bars_by_symbol.items():
                    if len(bars) < 360:
                        continue
                    index = pd.DatetimeIndex([price.date for price in bars])
                    closes[symbol] = pd.Series(
                        [price.close for price in bars], index=index
                    )
                    highs[symbol] = pd.Series(
                        [price.high for price in bars], index=index
                    )
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
                return RunBacktestResult.success(
                    BacktestOutcome(
                        status="no_history",
                        benchmark_note=benchmark_note,
                        benchmark_without_prices=benchmark_without_prices,
                        n_symbols=0,
                        start=None,
                        end_date=end_date,
                        summary=None,
                    )
                )
            n_symbols = sum(frame[0].shape[1] for frame in chunks)

            runner = StrategyRunner(
                size_pct=request.size_pct, stop=request.stop, fees=request.fees
            )
            start: date = (
                start_date if start_date is not None else list(union_idx)[300].date()
            )
            summary = runner.run_chunked(
                strategy, chunks, start=start, benchmark=benchmark_series
            )
        except Exception as error:
            return RunBacktestResult.error([f"Failed to run backtest: {error}"])
        return RunBacktestResult.success(
            BacktestOutcome(
                status="no_trades" if summary.n_trades == 0 else "done",
                benchmark_note=benchmark_note,
                benchmark_without_prices=benchmark_without_prices,
                n_symbols=n_symbols,
                start=start,
                end_date=end_date,
                summary=summary,
            )
        )
