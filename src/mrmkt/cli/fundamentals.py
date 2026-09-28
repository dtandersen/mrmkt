"""Fundamentals CLI commands (thin wrappers around fundamentals commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.import_fundamentals import ImportFundamentalsRequest
from mrmkt.command.show_fundamentals import ShowFundamentalsRequest

fundamentals_app = typer.Typer(
    no_args_is_help=True, help="Import and show as-reported fundamentals"
)


@fundamentals_app.command("import")
def import_fundamentals(
    ctx: typer.Context,
    symbols: list[str] | None = typer.Argument(None, help="Symbols to import"),
    provider: str = typer.Option(
        ..., "--provider", help="Fundamentals source (tiingo)"
    ),
    all_symbols: bool = typer.Option(
        False, "--all", help="Import every locally cataloged symbol"
    ),
    tag: str | None = typer.Option(None, "--tag", help="Import symbols with this tag"),
) -> None:
    """Import as-reported fundamentals into the local store."""
    handle(
        ctx,
        lambda factory: factory.import_fundamentals(provider=provider).execute(
            ImportFundamentalsRequest(
                provider=provider,
                symbols=symbols,
                all_symbols=all_symbols,
                tag=tag,
            )
        ),
        _echo_fundamentals_import,
    )


def _echo_fundamentals_import(outcome) -> None:
    if not outcome.selected_symbols:
        typer.echo("No symbols to import.")
        return
    typer.echo(
        f"Imported {outcome.result.imported} new fundamental row{'s' if outcome.result.imported != 1 else ''} for "
        f"{len(outcome.selected_symbols)} symbol{'s' if len(outcome.selected_symbols) != 1 else ''}."
    )
    if outcome.result.failed_batches:
        for batch in outcome.result.failed_batches:
            typer.echo(
                f"Failed to import fundamentals for: {', '.join(batch)}",
                err=True,
            )
        raise typer.Exit(code=1)


@fundamentals_app.command("show")
def show_fundamentals(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Symbol to show"),
) -> None:
    """Show stored fundamentals as deterministic tables."""
    handle(
        ctx,
        lambda factory: factory.show_fundamentals().execute(
            ShowFundamentalsRequest(symbol=symbol)
        ),
        _echo_fundamentals_view,
    )


def _echo_fundamentals_view(view) -> None:
    typer.echo("SYMBOL | DATE | NET_INCOME | WASO | CONSOLIDATED")
    for income in view.incomes:
        typer.echo(
            f"{income.symbol} | {income.date.isoformat()} | {income.netIncome:g} | "
            f"{income.waso:g} | {income.consolidated_net_income:g}"
        )
    typer.echo("SYMBOL | DATE | TOTAL_ASSETS | TOTAL_LIABILITIES")
    for balance in view.balances:
        typer.echo(
            f"{balance.symbol} | {balance.date.isoformat()} | {balance.totalAssets:g} | "
            f"{balance.totalLiabilities:g}"
        )
    typer.echo("SYMBOL | DATE | OP_CASH_FLOW | CAPEX | FREE_CASH_FLOW | DIVIDENDS")
    for cashflow in view.cashflows:
        typer.echo(
            f"{cashflow.symbol} | {cashflow.date.isoformat()} | "
            f"{cashflow.operating_cash_flow:g} | {cashflow.capital_expenditure:g} | "
            f"{cashflow.free_cash_flow:g} | {cashflow.dividend_payments:g}"
        )
    typer.echo("SYMBOL | DATE | PRICE | SHARES | MARKET_CAP")
    for enterprise in view.enterprise_values:
        typer.echo(
            f"{enterprise.symbol} | {enterprise.date.isoformat()} | "
            f"{enterprise.stock_price:g} | {enterprise.shares_outstanding:g} | "
            f"{enterprise.market_cap:g}"
        )
