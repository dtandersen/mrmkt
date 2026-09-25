"""Price CLI commands (thin wrappers around price commands)."""

import typer

from mrmkt.command.prices_freshness import render_csv
from mrmkt.composition import CliDependencies, resolve_cli_dependencies

prices_app = typer.Typer(no_args_is_help=True, help="Import and list historical prices")


@prices_app.command("import")
def import_prices(
    ctx: typer.Context,
    symbols: list[str] | None = typer.Argument(None, help="Symbols to import"),
    provider: str = typer.Option(..., "--provider", help="Price source (currently: alpaca)"),
    all_symbols: bool = typer.Option(False, "--all", help="Import every locally cataloged symbol"),
    tag: str | None = typer.Option(None, "--tag", help="Import symbols with this tag"),
    from_date: str = typer.Option(..., "--from", help="Start date (YYYY-MM-DD or duration such as 180d)"),
    to_date: str | None = typer.Option(None, "--to", help="End date (defaults to today)"),
) -> None:
    """Import bounded daily price history into the local store."""
    env: CliDependencies = resolve_cli_dependencies(ctx)
    try:
        import_command = env.command_factory.import_prices()
        outcome = import_command.execute(
                provider=provider,
                symbols=symbols,
                all_symbols=all_symbols,
                tag=tag,
                from_date=from_date,
                to_date=to_date,
            )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to import prices from Alpaca: {error}", err=True)
        raise typer.Exit(code=1) from error

    if not outcome.selected_symbols:
        typer.echo("No symbols to import.")
        return
    typer.echo(
        f"Imported {outcome.result.imported} new daily bar{'s' if outcome.result.imported != 1 else ''} for "
        f"{len(outcome.selected_symbols)} symbol{'s' if len(outcome.selected_symbols) != 1 else ''}."
    )
    if outcome.result.failed_batches:
        for batch in outcome.result.failed_batches:
            typer.echo(
                f"Failed to import prices for: {', '.join(batch)}",
                err=True,
            )
        raise typer.Exit(code=1)


@prices_app.command("list")
def list_prices(
    ctx: typer.Context,
    symbols: list[str] = typer.Argument(..., help="One or more symbols to list"),
    from_date: str | None = typer.Option(None, "--from", help="Start date (ISO date or duration such as 7d)"),
    to_date: str | None = typer.Option(None, "--to", help="End date (defaults to today when --from is used)"),
) -> None:
    """List stored daily bars as a deterministic table."""
    env: CliDependencies = resolve_cli_dependencies(ctx)
    try:
        list_command = env.command_factory.list_prices()
        prices = list_command.execute(
            symbols=symbols, from_date=from_date, to_date=to_date
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to list prices: {error}", err=True)
        raise typer.Exit(code=1) from error

    if not prices:
        typer.echo("No prices found.")
        return

    typer.echo("SYMBOL | DATE | OPEN | HIGH | LOW | CLOSE | VOLUME")
    for price in prices:
        typer.echo(
            f"{price.symbol} | {price.date.isoformat()} | {price.open:g} | "
            f"{price.high:g} | {price.low:g} | {price.close:g} | {price.volume:g}"
        )


@prices_app.command("freshness")
def run_prices_freshness(
    ctx: typer.Context,
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable; default: all symbols)"),
    exclude_tags: list[str] | None = typer.Option(None, "--exclude-tag", help="Exclude symbols with this tag (repeatable)"),
    lookback_days: int = typer.Option(365, "--lookback-days", help="Bar-quality window in days"),
    stale_after_days: int = typer.Option(5, "--stale-after", help="Flag symbols with no bar for longer than this"),
    gap_threshold: float = typer.Option(0.20, "--gap-threshold", help="Overnight-gap heuristic threshold as a fraction"),
) -> None:
    """Report price staleness and bar-quality flags; prints deterministic CSV."""
    env: CliDependencies = resolve_cli_dependencies(ctx)
    try:
        freshness_command = env.command_factory.check_freshness()
        result = freshness_command.execute(
            tags=tags,
            exclude_tags=exclude_tags,
            lookback_days=lookback_days,
            stale_after_days=stale_after_days,
            gap_threshold=gap_threshold,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to check freshness: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(render_csv(result), nl=False)
