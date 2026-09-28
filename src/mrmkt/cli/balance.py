"""Balance CLI commands (thin wrappers around balance commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.show_balance import ShowBalanceRequest
from mrmkt.entity.trading import Account

balance_app = typer.Typer(no_args_is_help=True, help="Show paper-account balance")


def _render_balance_csv(account: Account) -> str:
    lines = ["equity,cash,buying_power,portfolio_value,currency"]
    lines.append(
        ",".join(
            [
                str(account.equity),
                str(account.cash),
                str(account.buying_power),
                "" if account.portfolio_value is None else str(account.portfolio_value),
                account.currency,
            ]
        )
    )
    return "\n".join(lines) + "\n"


@balance_app.command("show")
def balance_show(ctx: typer.Context) -> None:
    """Show the paper-account balance as CSV."""
    handle(
        ctx,
        lambda factory: factory.show_balance().execute(ShowBalanceRequest()),
        lambda account: typer.echo(_render_balance_csv(account), nl=False),
    )
