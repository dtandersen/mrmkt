"""Order CLI commands (thin wrappers around order commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.cancel_order import CancelOrderRequest
from mrmkt.command.create_order import CreateOrderRequest
from mrmkt.command.list_orders import ListOrdersRequest
from mrmkt.command.show_order import ShowOrderRequest
from mrmkt.entity.trading import TradingOrder

order_app = typer.Typer(no_args_is_help=True, help="Manage paper-account orders")


def _render_orders_csv(orders: list[TradingOrder]) -> str:
    lines = [
        "id,symbol,side,qty,filled_qty,limit_price,stop_price,status,type,time_in_force"
    ]
    for order in orders:
        lines.append(
            ",".join(
                [
                    order.id,
                    order.symbol,
                    order.side,
                    str(order.qty),
                    "" if order.filled_qty is None else str(order.filled_qty),
                    "" if order.limit_price is None else str(order.limit_price),
                    "" if order.stop_price is None else str(order.stop_price),
                    order.status,
                    order.order_type,
                    "" if order.time_in_force is None else order.time_in_force,
                ]
            )
        )
    return "\n".join(lines) + "\n"


@order_app.command("create")
def order_create(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Symbol to trade"),
    buy: float | None = typer.Option(None, "--buy", help="Buy quantity in shares"),
    sell: float | None = typer.Option(None, "--sell", help="Sell quantity in shares"),
    price: float = typer.Option(..., "--price", help="Limit price"),
    stop: float | None = typer.Option(
        None, "--stop", help="Stop-loss price (OTO leg when given)"
    ),
    tif: str = typer.Option(
        "day", "--tif", help="Time in force: day (house rule) or gtc"
    ),
) -> None:
    """Submit a DAY limit order (resting limit fills only on the touch)."""
    if (buy is None) == (sell is None):
        raise typer.BadParameter("provide exactly one of --buy or --sell")
    side = "buy" if buy is not None else "sell"
    qty = buy if buy is not None else sell
    assert qty is not None
    handle(
        ctx,
        lambda factory: factory.create_order().execute(
            CreateOrderRequest(
                symbol=symbol,
                side=side,
                qty=qty,
                limit_price=price,
                stop_price=stop,
                time_in_force=tif,
            )
        ),
        lambda order: typer.echo(_render_orders_csv([order]), nl=False),
    )


@order_app.command("list")
def orders_list(
    ctx: typer.Context,
    status: str = typer.Option("open", "--status", help="open, closed, or all"),
) -> None:
    """List paper-account orders as deterministic CSV."""
    handle(
        ctx,
        lambda factory: factory.list_orders().execute(ListOrdersRequest(status=status)),
        lambda orders: typer.echo(_render_orders_csv(orders), nl=False),
    )


@order_app.command("show")
def order_show(
    ctx: typer.Context,
    order_id: str = typer.Argument(..., help="Order id from order list"),
) -> None:
    """Show a single paper-account order as CSV."""
    handle(
        ctx,
        lambda factory: factory.show_order().execute(
            ShowOrderRequest(order_id=order_id)
        ),
        lambda order: typer.echo(_render_orders_csv([order]), nl=False),
    )


@order_app.command("cancel")
def order_cancel(
    ctx: typer.Context,
    order_id: str = typer.Argument(..., help="Order id from order list"),
) -> None:
    """Cancel an open paper-account order."""
    handle(
        ctx,
        lambda factory: factory.cancel_order().execute(
            CancelOrderRequest(order_id=order_id)
        ),
        lambda order: typer.echo(f"canceled order {order.id}"),
    )
