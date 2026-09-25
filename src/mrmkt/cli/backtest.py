"""Backtest CLI commands (thin wrappers around backtest commands)."""

import typer

from mrmkt.command.backtest_run import RunBacktest
from mrmkt.composition import resolve_cli_dependencies

backtest_app = typer.Typer(no_args_is_help=True, help="Backtest signal portfolios over stored prices")


@backtest_app.command("run")
def run_backtest(
    ctx: typer.Context,
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
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(RunBacktest) as backtest_command:
            outcome = backtest_command.execute(
                symbols,
                all_symbols,
                tags,
                from_date,
                to_date,
                strategy_name,
                params_text,
                benchmark,
                size_pct,
                stop,
                fees,
                chunk_size,
            )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to run backtest: {error}", err=True)
        raise typer.Exit(code=1) from error

    if outcome.status == "no_symbols":
        typer.echo("No symbols to backtest.")
        return
    if outcome.benchmark_note is not None:
        typer.echo(outcome.benchmark_note)
    if outcome.benchmark_without_prices is not None:
        typer.echo(
            f"Benchmark {outcome.benchmark_without_prices} has no stored prices; "
            "strategies fall back to the universe mean."
        )
    if outcome.status == "no_history":
        typer.echo("No symbols with enough history to backtest.")
        return
    if outcome.status == "no_trades":
        typer.echo("No trades generated in the test window.")
        return
    summary = outcome.summary
    typer.echo(f"Symbols: {outcome.n_symbols}  Test window: {outcome.start} to {outcome.end_date}")
    typer.echo(f"Trades: {summary.n_trades}  Win rate: {summary.win_rate:.1%}")
    typer.echo(f"Avg win: {summary.avg_win:+.2%}  Avg loss: {summary.avg_loss:+.2%}")
    typer.echo(f"Expectancy: {summary.expectancy:+.3%}  Profit factor: {summary.profit_factor:.2f}")
    typer.echo(f"Avg hold: {summary.avg_hold_days:.1f}d  Exposure: {summary.exposure:.1%}")
    typer.echo(
        f"CAGR: {summary.cagr:+.1%}  Sharpe: {summary.sharpe:.2f}  Max DD: {summary.max_drawdown:.1%}"
    )
