"""Current signal discovery command."""

from collections.abc import Callable

import typer

from mrmkt.backtest.strategy import parse_params
from mrmkt.command import _shared, signals_app
from mrmkt.command._shared import normalize_symbol, normalize_tag, parse_cli_date
from mrmkt.usecase.signals_current import (
    SignalsRequest,
    SignalsUseCase,
)
from mrmkt.usecase.signals_current import (
    render_csv as render_signals_csv,
)


@signals_app.command("current")
def run_signals_current(
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable; default: all symbols)"),
    exclude_tags: list[str] | None = typer.Option(None, "--exclude-tag", help="Exclude symbols with this tag (repeatable)"),
    as_of: str | None = typer.Option(None, "--as-of", help="Signal date (defaults to latest stored bar)"),
    strategy_name: str = typer.Option("buy-red", "--strategy", help="Strategy name from the registry"),
    params_text: str | None = typer.Option(None, "--params", help="Strategy params as k=v,... (defaults when omitted)"),
    benchmark: str = typer.Option(
        "SPY",
        "--benchmark",
        help="Market symbol for regime gating (non-tradable context; blank disables lookup)",
    ),
    include_benchmark: bool = typer.Option(
        False,
        "--include-benchmark",
        help="Score the benchmark symbol as a tradable candidate too",
    ),
    top: int | None = typer.Option(None, "--top", help="Keep only the first N symbol rows"),
) -> None:
    """Show per-symbol strategy signals at a stored bar; prints deterministic CSV."""
    if top is not None and top < 1:
        raise typer.BadParameter("--top must be at least 1")
    today = _shared.create_clock().today()
    try:
        as_of_date = parse_cli_date(as_of, today) if as_of is not None else None
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    try:
        params = parse_params(params_text)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        result = SignalsUseCase(repository).execute(
            SignalsRequest(
                include_tags=[normalize_tag(tag) for tag in (tags or [])],
                exclude_tags=[normalize_tag(tag) for tag in (exclude_tags or [])],
                as_of=as_of_date,
                strategy_name=strategy_name,
                params=params,
                benchmark_symbol=normalize_symbol(benchmark) if benchmark and benchmark.strip() else None,
                include_benchmark=include_benchmark,
                top_n=top,
            )
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to inspect signals: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(render_signals_csv(result), nl=False)
