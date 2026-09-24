"""mrmkt command-line entrypoint (thin Typer wiring over command modules)."""

import typer

from mrmkt.command import ranges, screen, watch
from mrmkt.command._shared import (
    _resolve_signal,
    create_alpaca_client,
    create_alpaca_data_client,
    create_clock,
    create_local_ticker_repository,
    load_local_config,
    normalize_symbol,
    normalize_tag,
    parse_cli_date,
    split_benchmark_symbol,
)
from mrmkt.command import (
    backtest_app,
    indicators_app,
    prices_app,
    signals_app,
    symbols_app,
    trigger_app,
)
from mrmkt.command import (  # noqa: F401 -- side-effect registration of commands
    backtest_run,
    indicators_risk_range,
    indicators_sma,
    indicators_vol_of_vol,
    indicators_vol_of_vol_percentile,
    indicators_volatility,
    indicators_volatility_percentile,
    prices_freshness,
    prices_import,
    prices_list,
    signals_current,
    symbols_import,
    symbols_label,
    symbols_list,
    symbols_unlabel,
    trigger_create,
    trigger_disable,
    trigger_enable,
    trigger_list,
    trigger_remove,
)

__all__ = [
    "app",
    "create_alpaca_client",
    "create_alpaca_data_client",
    "create_clock",
    "create_local_ticker_repository",
    "load_local_config",
    "normalize_symbol",
    "normalize_tag",
    "parse_cli_date",
    "split_benchmark_symbol",
]

app = typer.Typer(no_args_is_help=True, help="MrMkt stock-market tools")
app.add_typer(symbols_app, name="symbols")
app.add_typer(prices_app, name="prices")
app.add_typer(indicators_app, name="indicators")
app.add_typer(backtest_app, name="backtest")
app.add_typer(signals_app, name="signals")
app.add_typer(trigger_app, name="trigger")


@app.command("screen")
def run_screen(
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable; default: all symbols)"),
    exclude_tags: list[str] | None = typer.Option(None, "--exclude-tag", help="Exclude symbols with this tag (repeatable)"),
    as_of: str | None = typer.Option(None, "--as-of", help="Screening date (defaults to latest stored bar)"),
    mode: str = typer.Option("technical-only", "--mode", help="Screening mode (only technical-only: fundamentals unavailable)"),
    min_price: float = typer.Option(0.0, "--min-price", help="Minimum last close"),
    min_dollar_vol: float = typer.Option(0.0, "--min-dollar-vol", help="Minimum 63D median dollar volume"),
    min_bars: int = typer.Option(0, "--min-bars", help="Minimum bars on/before as-of"),
    max_stale_days: int | None = typer.Option(None, "--max-stale-days", help="Exclude symbols whose last bar is older than this (calendar days; default keeps stale names)"),
    top: int | None = typer.Option(None, "--top", help="Keep only the top N ranked rows"),
) -> None:
    """Rank a tag universe on point-in-time technicals; prints deterministic CSV."""
    screen.run(
        tags=tags,
        exclude_tags=exclude_tags,
        as_of=as_of,
        mode=mode,
        min_price=min_price,
        min_dollar_vol=min_dollar_vol,
        min_bars=min_bars,
        max_stale_days=max_stale_days,
        top=top,
    )


@app.command("ranges")
def run_ranges(
    symbols: list[str] | None = typer.Argument(None, help="Symbols to include"),
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable)"),
    signal: str = typer.Option("risk-range", "--signal", help="Signal source for ranges (only 'risk-range')"),
    as_of: str | None = typer.Option(None, "--as-of", help="Range date (defaults to latest stored bar)"),
    horizon: int = typer.Option(15, "--horizon", help="Range horizon in trading days"),
    vol_period: int = typer.Option(21, "--vol-period", help="Trailing returns for realized volatility"),
    width: float = typer.Option(0.5, "--width", help="Range half-width in vol-scaled units"),
    anchor_period: int = typer.Option(5, "--anchor", help="Trailing mean the range is centered on"),
) -> None:
    """Print deterministic risk-range bands from stored bars."""
    _resolve_signal(signal)
    ranges.run(
        symbols=symbols,
        tags=tags,
        as_of=as_of,
        horizon=horizon,
        vol_period=vol_period,
        width=width,
        anchor_period=anchor_period,
    )


@app.command("watch")
def run_watch(
    symbols: list[str] | None = typer.Argument(None, help="Symbols to include"),
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable)"),
    trigger_ids: list[int] | None = typer.Option(None, "--trigger-id", help="Stored trigger id to watch (repeatable)"),
    all_triggers: bool = typer.Option(False, "--all-triggers", help="Watch every enabled stored trigger"),
    signal: str = typer.Option("risk-range", "--signal", help="Signal source to watch (only 'risk-range')"),
    sinks: list[str] | None = typer.Option(None, "--sink", help="Alert sink: stdout, file, ntfy (repeatable)"),
    sink_file: str | None = typer.Option(None, "--sink-file", help="Append path for the file sink"),
    feed: str = typer.Option("iex", "--feed", help="Alpaca data feed: iex or sip"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Replay stored daily lows as ticks; no network"),
    session_policy: str = typer.Option("regular", "--session-policy", help="Sessions that may fire: regular or extended"),
    as_of: str | None = typer.Option(None, "--as-of", help="Levels date (defaults to latest stored bar)"),
    verbose: bool = typer.Option(False, "--verbose", help="Also print ignored non-trigger ticks"),
) -> None:
    """Watch live prices and alert once per buy-level touch (deduped to re-arm)."""
    _resolve_signal(signal)
    watch.run(
        symbols=symbols,
        tags=tags,
        sinks=sinks,
        sink_file=sink_file,
        feed=feed,
        dry_run=dry_run,
        session_policy=session_policy,
        as_of=as_of,
        verbose=verbose,
        trigger_ids=trigger_ids,
        all_triggers=all_triggers,
    )
