"""Symbol catalog CLI commands (thin wrappers around symbol commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.import_symbols import ImportSymbolsRequest
from mrmkt.command.list_symbols import ListSymbolsRequest
from mrmkt.command.symbols_label import LabelSymbolsRequest
from mrmkt.command.symbols_unlabel import UnlabelSymbolsRequest

symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")


@symbols_app.command("import")
def import_symbols(
    ctx: typer.Context,
    provider: str = typer.Option(
        ..., "--provider", help="Symbol source (currently: alpaca)"
    ),
) -> None:
    """Import the remote symbol catalog into the local repository."""
    handle(
        ctx,
        lambda factory: factory.import_symbols().execute(
            ImportSymbolsRequest(provider=provider)
        ),
        lambda count: typer.echo(
            f"Imported {count} newly imported symbol{'s' if count != 1 else ''}."
        ),
    )


@symbols_app.command("list")
def list_symbols(
    ctx: typer.Context,
    tag: str | None = typer.Option(
        None, "--tag", help="Only show symbols with this tag"
    ),
) -> None:
    """List stored symbols as a deterministic table."""
    handle(
        ctx,
        lambda factory: factory.list_symbols().execute(ListSymbolsRequest(tag=tag)),
        _echo_symbol_list,
    )


def _echo_symbol_list(tickers) -> None:
    if not tickers:
        typer.echo("No symbols found.")
        return
    typer.echo("SYMBOL | EXCHANGE | TYPE")
    for ticker in tickers:
        typer.echo(f"{ticker.ticker} | {ticker.exchange} | {ticker.type}")


@symbols_app.command("label")
def label_symbols(ctx: typer.Context, symbols: str, tag: str) -> None:
    """Tag stored symbols; prints how many assignments changed."""
    handle(
        ctx,
        lambda factory: factory.label_symbols().execute(
            LabelSymbolsRequest(symbols=symbols, tag=tag)
        ),
        _echo_tag_change,
    )


@symbols_app.command("unlabel")
def unlabel_symbols(ctx: typer.Context, symbols: str, tag: str) -> None:
    """Untag stored symbols; prints how many assignments changed."""
    handle(
        ctx,
        lambda factory: factory.unlabel_symbols().execute(
            UnlabelSymbolsRequest(symbols=symbols, tag=tag)
        ),
        _echo_tag_change,
    )


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
