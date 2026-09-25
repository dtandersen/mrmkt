"""Symbol catalog CLI commands (thin wrappers around symbol commands)."""

import typer

from mrmkt.command.list_symbols import ListSymbols
from mrmkt.command.symbols_import import ImportSymbols
from mrmkt.command.symbols_label import LabelSymbols
from mrmkt.command.symbols_unlabel import UnlabelSymbols
from mrmkt.composition import resolve_cli_dependencies

symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")


@symbols_app.command("import")
def import_symbols(
    ctx: typer.Context,
    provider: str = typer.Option(..., "--provider", help="Symbol source (currently: alpaca)"),
) -> None:
    """Import the remote symbol catalog into the local repository."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(ImportSymbols) as import_command:
            count = import_command.execute(provider)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to import symbols from Alpaca: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Imported {count} newly imported symbol{'s' if count != 1 else ''}.")


@symbols_app.command("list")
def list_symbols(
    ctx: typer.Context,
    tag: str | None = typer.Option(None, "--tag", help="Only show symbols with this tag"),
) -> None:
    """List stored symbols as a deterministic table."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(ListSymbols) as list_command:
            tickers = list_command.execute(tag)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to list symbols: {error}", err=True)
        raise typer.Exit(code=1) from error

    if not tickers:
        typer.echo("No symbols found.")
        return

    typer.echo("SYMBOL | EXCHANGE | TYPE")
    for ticker in tickers:
        typer.echo(f"{ticker.ticker} | {ticker.exchange} | {ticker.type}")


@symbols_app.command("label")
def label_symbols(ctx: typer.Context, symbols: str, tag: str) -> None:
    """Tag stored symbols; prints how many assignments changed."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(LabelSymbols) as label_command:
            result = label_command.execute(symbols, tag)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to label symbols: {error}", err=True)
        raise typer.Exit(code=1) from error
    _echo_tag_change(result)


@symbols_app.command("unlabel")
def unlabel_symbols(ctx: typer.Context, symbols: str, tag: str) -> None:
    """Untag stored symbols; prints how many assignments changed."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(UnlabelSymbols) as unlabel_command:
            result = unlabel_command.execute(symbols, tag)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to unlabel symbols: {error}", err=True)
        raise typer.Exit(code=1) from error
    _echo_tag_change(result)


def _echo_tag_change(result) -> None:
    action = "Added" if result.added else "Removed"
    typer.echo(
        f"{action} {result.changed_count} '{result.tag}' tag assignment"
        f"{'s' if result.changed_count != 1 else ''} for {result.matched_count} symbols."
    )
    if result.unmatched_count:
        typer.echo(
            f"Skipped {result.unmatched_count} symbols not in the local ticker catalog.",
            err=True,
        )
