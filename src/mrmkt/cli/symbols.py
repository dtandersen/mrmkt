"""Symbol catalog CLI commands (thin wrappers around symbol commands)."""

import typer

from mrmkt.command.import_symbols import ImportSymbolsRequest
from mrmkt.composition import AppContext, resolve_cli_dependencies

symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")


@symbols_app.command("import")
def import_symbols(
    ctx: typer.Context,
    provider: str = typer.Option(..., "--provider", help="Symbol source (currently: alpaca)"),
) -> None:
    """Import the remote symbol catalog into the local repository."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        import_command = env.command_factory.import_symbols()
        result = import_command.execute(ImportSymbolsRequest(provider=provider))
    except Exception as error:
        typer.echo(f"Failed to import symbols from Alpaca: {error}", err=True)
        raise typer.Exit(code=1) from error
    if not result.success:
        raise typer.BadParameter("; ".join(result.errors))
    count = result.imported_count
    typer.echo(f"Imported {count} newly imported symbol{'s' if count != 1 else ''}.")


@symbols_app.command("list")
def list_symbols(
    ctx: typer.Context,
    tag: str | None = typer.Option(None, "--tag", help="Only show symbols with this tag"),
) -> None:
    """List stored symbols as a deterministic table."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        list_command = env.command_factory.list_symbols()
        tickers = list_command.execute(tag=tag)
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
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        label_command = env.command_factory.label_symbols()
        result = label_command.execute(symbols=symbols, tag=tag)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to label symbols: {error}", err=True)
        raise typer.Exit(code=1) from error
    _echo_tag_change(result)


@symbols_app.command("unlabel")
def unlabel_symbols(ctx: typer.Context, symbols: str, tag: str) -> None:
    """Untag stored symbols; prints how many assignments changed."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        unlabel_command = env.command_factory.unlabel_symbols()
        result = unlabel_command.execute(symbols=symbols, tag=tag)
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
