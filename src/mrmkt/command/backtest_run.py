"""Backtest command."""

from collections.abc import Callable
from datetime import date

import pandas as pd
import typer

from mrmkt.backtest.strategy import StrategyRunner, build_strategy, parse_params
from mrmkt.command import _shared, backtest_app
from mrmkt.command._shared import (
    normalize_symbol,
    normalize_tag,
    parse_cli_date,
    split_benchmark_symbol,
)


@backtest_app.command("run")
def run_backtest(
    symbols: list[str] | None = typer.Argument(None, help="Symbols to include"),
    all_symbols: bool = typer.Option(False, "--all", help="Include every locally cataloged symbol"),
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable)"),
    from_date: str | None = typer.Option(None, "--from", help="Test window start (defaults to auto warm-up)"),
    to_date: str | None = typer.Option(None, "--to", help="Test window end (defaults to today)"),
    strategy_name: str = typer.Option("buy-red", "--strategy", help="Strategy name from the registry"),
    params_text: str | None = typer.Option(None, "--params", help="Strategy params as k=v,... (defaults when omitted)"),
    benchmark: str = typer.Option(
        "SPY",
        "--benchmark",
        help="Market symbol for regime gating (non-tradable context; blank disables lookup)",
    ),
    size_pct: float = typer.Option(2.0, help="Percent of equity per position"),
    stop: float = typer.Option(0.08, help="Stop-loss fraction"),
    fees: float = typer.Option(0.0, "--fees", help="All-in friction per side as a fraction (0 = none)"),
    chunk_size: int = typer.Option(250, "--chunk-size", help="Symbols loaded and simulated per chunk"),
) -> None:
    """Backtest a strategy over stored prices with vectorbt."""
    selector_count = sum((bool(symbols), all_symbols, bool(tags)))
    if selector_count != 1:
        raise typer.BadParameter("provide symbols, --all, or --tag")
    if not 0 < size_pct <= 100:
        raise typer.BadParameter("size_pct must be between 0 and 100")
    if not 0 < stop < 1:
        raise typer.BadParameter("stop must be between 0 and 1")
    if fees < 0:
        raise typer.BadParameter("fees must be >= 0")
    if chunk_size < 1:
        raise typer.BadParameter("chunk-size must be at least 1")

    today = _shared.create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    try:
        strategy = build_strategy(strategy_name, parse_params(params_text))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        if tags:
            selected = sorted(
                {s for tag in tags for s in repository.get_symbols_by_tag(normalize_tag(tag))}
            )
        elif all_symbols:
            selected = sorted({ticker.ticker for ticker in repository.get_tickers()})
        else:
            selected = [normalize_symbol(symbol) for symbol in (symbols or [])]
        if not selected:
            typer.echo("No symbols to backtest.")
            return

        benchmark_symbol = normalize_symbol(benchmark) if benchmark and benchmark.strip() else ""
        selected, benchmark_note = split_benchmark_symbol(selected, benchmark_symbol)
        if benchmark_note is not None:
            typer.echo(benchmark_note)
        benchmark_series: pd.Series | None = None
        if benchmark_symbol:
            bench_bars = list(
                repository.list_prices_for_symbols([benchmark_symbol], date.min, end_date)
            )
            if bench_bars:
                bench_index = pd.DatetimeIndex([price.date for price in bench_bars])
                benchmark_series = pd.Series(
                    [price.close for price in bench_bars], index=bench_index
                ).sort_index()
            else:
                typer.echo(
                    f"Benchmark {benchmark_symbol} has no stored prices; "
                    "strategies fall back to the universe mean."
                )

        chunks = []
        union_idx: pd.DatetimeIndex = pd.DatetimeIndex([])
        for offset in range(0, len(selected), chunk_size):
            closes, highs, lows = {}, {}, {}
            bars_by_symbol: dict = {}
            for price in repository.list_prices_for_symbols(
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
            typer.echo("No symbols with enough history to backtest.")
            return
        n_symbols = sum(frame[0].shape[1] for frame in chunks)

        runner = StrategyRunner(size_pct=size_pct, stop=stop, fees=fees)
        start: date = start_date if start_date is not None else list(union_idx)[300].date()
        result = runner.run_chunked(strategy, chunks, start=start, benchmark=benchmark_series)
    except Exception as error:
        typer.echo(f"Failed to run backtest: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    if result.n_trades == 0:
        typer.echo("No trades generated in the test window.")
        return
    typer.echo(f"Symbols: {n_symbols}  Test window: {start} to {end_date}")
    typer.echo(f"Trades: {result.n_trades}  Win rate: {result.win_rate:.1%}")
    typer.echo(f"Avg win: {result.avg_win:+.2%}  Avg loss: {result.avg_loss:+.2%}")
    typer.echo(f"Expectancy: {result.expectancy:+.3%}  Profit factor: {result.profit_factor:.2f}")
    typer.echo(f"Avg hold: {result.avg_hold_days:.1f}d  Exposure: {result.exposure:.1%}")
    typer.echo(
        f"CAGR: {result.cagr:+.1%}  Sharpe: {result.sharpe:.2f}  Max DD: {result.max_drawdown:.1%}"
    )
