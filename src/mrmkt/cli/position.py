"""Position CLI commands (thin wrappers around position commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.list_positions import ListPositionsRequest
from mrmkt.entity.trading import Position

position_app = typer.Typer(no_args_is_help=True, help="List paper-account positions")


def _render_positions_csv(positions: list[Position]) -> str:
    lines = ["symbol,qty,avg_entry,current,market_value,unrealized_pl"]
    for position in positions:
        lines.append(
            ",".join(
                [
                    position.symbol,
                    str(position.qty),
                    str(position.avg_entry_price),
                    ""
                    if position.current_price is None
                    else str(position.current_price),
                    "" if position.market_value is None else str(position.market_value),
                    ""
                    if position.unrealized_pl is None
                    else str(position.unrealized_pl),
                ]
            )
        )
    return "\n".join(lines) + "\n"


@position_app.command("list")
def positions_list(ctx: typer.Context) -> None:
    """List open paper-account positions as deterministic CSV."""
    handle(
        ctx,
        lambda factory: factory.list_positions().execute(ListPositionsRequest()),
        lambda positions: typer.echo(_render_positions_csv(positions), nl=False),
    )
