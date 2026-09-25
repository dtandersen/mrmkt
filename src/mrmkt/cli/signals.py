"""Signals CLI commands (thin wrappers around signal commands)."""

import typer

from mrmkt.command.signals_current import render_csv
from mrmkt.composition import CliDependencies, resolve_cli_dependencies

signals_app = typer.Typer(no_args_is_help=True, help="Inspect current strategy signals over stored prices")


@signals_app.command("current")
def run_signals_current(
    ctx: typer.Context,
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
    env: CliDependencies = resolve_cli_dependencies(ctx)
    try:
        signals_command = env.command_factory.current_signals()
        result = signals_command.execute(
            tags=tags,
            exclude_tags=exclude_tags,
            as_of=as_of,
            strategy_name=strategy_name,
            params_text=params_text,
            benchmark=benchmark,
            include_benchmark=include_benchmark,
            top=top,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to inspect signals: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(render_csv(result), nl=False)
