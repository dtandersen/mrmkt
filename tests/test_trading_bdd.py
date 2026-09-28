"""BDD coverage for paper-trading position and order commands."""

from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    is_,
    not_,
    not_none,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.base import BaseResult
from mrmkt.command.cancel_order import CancelOrder, CancelOrderRequest
from mrmkt.command.create_order import CreateOrder, CreateOrderRequest
from mrmkt.command.list_orders import ListOrders, ListOrdersRequest
from mrmkt.command.list_positions import ListPositions, ListPositionsRequest
from mrmkt.command.show_balance import ShowBalance, ShowBalanceRequest
from mrmkt.command.show_order import ShowOrder, ShowOrderRequest
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.ext.alpaca_trading import AlpacaTradingGateway

scenarios(
    "features/cli/balance_show.feature",
    "features/cli/position_list.feature",
    "features/cli/order_create.feature",
    "features/cli/order_list.feature",
    "features/cli/order_show_cancel.feature",
    "features/command/list_positions.feature",
    "features/command/show_balance.feature",
    "features/command/trading_orders.feature",
)


@pytest.fixture
def trading_context():
    return SimpleNamespace(result=None, cli_result=None, failed=False, error="")


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    rows = []
    for row in datatable[1:]:
        record = dict(zip(headers, row, strict=True))
        rows.append(
            {key: (value if value != "" else None) for key, value in record.items()}
        )
    return rows


def _gateway(alpaca_client):
    return AlpacaTradingGateway(alpaca_client)


def _deps(trading_context, financial_repository, alpaca_client):
    return cli_dependencies_for_testing(
        repository=financial_repository,
        alpaca_client=alpaca_client,
    )


def _invoke_cli(trading_context, financial_repository, alpaca_client, args):
    trading_context.result = None
    trading_context.cli_result = CliRunner().invoke(
        cli.app, args, obj=_deps(trading_context, financial_repository, alpaca_client)
    )


def _record(trading_context, result: BaseResult):
    trading_context.result = result
    trading_context.cli_result = None
    trading_context.failed = not result.is_success()
    trading_context.error = "; ".join(result.errors)


def _coerce_position(row):
    return {
        "symbol": row["symbol"],
        "qty": float(row["qty"]),
        "avg_entry_price": float(row["avg_entry_price"]),
        "current_price": float(row["current_price"])
        if row.get("current_price")
        else None,
        "market_value": float(row["market_value"]) if row.get("market_value") else None,
        "unrealized_pl": float(row["unrealized_pl"])
        if row.get("unrealized_pl")
        else None,
    }


def _coerce_order(row):
    def _num(key):
        value = row.get(key)
        return None if value in (None, "") else float(value)

    return {
        "id": row["id"],
        "symbol": row["symbol"],
        "side": row.get("side") or "buy",
        "qty": float(row["qty"]),
        "order_type": row.get("order_type") or "limit",
        "type": row.get("order_type") or "limit",
        "status": row.get("status") or "new",
        "limit_price": _num("limit_price"),
        "stop_price": _num("stop_price"),
        "filled_qty": _num("filled_qty"),
        "filled_avg_price": _num("filled_avg_price"),
        "time_in_force": row.get("time_in_force") or "gtc",
    }


@given("the paper account holds these positions:")
def paper_holds_positions(datatable, alpaca_client):
    alpaca_client.set_positions(
        [_coerce_position(row) for row in _table_rows(datatable)]
    )


@given("the paper account holds no positions")
def paper_holds_no_positions(alpaca_client):
    alpaca_client.set_positions([])


@given("the paper positions request fails")
def paper_positions_request_fails(alpaca_client):
    alpaca_client.positions_error = RuntimeError("paper trading unavailable")


@given("the paper account has these orders:")
def paper_has_orders(datatable, alpaca_client):
    alpaca_client.set_orders([_coerce_order(row) for row in _table_rows(datatable)])


@given("the paper account has no orders")
def paper_has_no_orders(alpaca_client):
    alpaca_client.set_orders([])


@given("the paper order request fails")
def paper_order_request_fails(alpaca_client):
    alpaca_client.orders_error = RuntimeError("paper trading unavailable")


@given("the paper balance request fails")
def paper_balance_request_fails(alpaca_client):
    alpaca_client.account_error = RuntimeError("paper trading unavailable")


@given("the paper account balance is:")
def paper_account_balance(datatable, alpaca_client):
    row = _table_rows(datatable)[0]
    alpaca_client.set_account(
        {
            "equity": row["equity"],
            "cash": row["cash"],
            "buying_power": row["buying_power"],
            "portfolio_value": row.get("portfolio_value"),
            "currency": row.get("currency") or "USD",
        }
    )


@when(parsers.parse('I execute "{command}"'))
def execute_trading_command(
    trading_context, command, financial_repository, alpaca_client
):
    args = split(command)
    _invoke_cli(trading_context, financial_repository, alpaca_client, args[1:])


@when("I list paper positions")
def list_paper_positions(trading_context, alpaca_client):
    _record(
        trading_context,
        ListPositions(_gateway(alpaca_client)).execute(ListPositionsRequest()),
    )


@when("I list paper orders")
def list_paper_orders(trading_context, alpaca_client):
    _record(
        trading_context,
        ListOrders(_gateway(alpaca_client)).execute(ListOrdersRequest(status="open")),
    )


@when(parsers.parse('I list paper orders with status "{status}"'))
def list_paper_orders_with_status(trading_context, status, alpaca_client):
    _record(
        trading_context,
        ListOrders(_gateway(alpaca_client)).execute(ListOrdersRequest(status=status)),
    )


@when(
    parsers.parse(
        'I create a paper buy of {qty} "{symbol}" at {price} stopping at {stop}'
    )
)
def create_paper_buy(trading_context, qty, symbol, price, stop, alpaca_client):
    stop_price = None if stop == "nothing" else float(stop)
    _record(
        trading_context,
        CreateOrder(_gateway(alpaca_client)).execute(
            CreateOrderRequest(
                symbol=symbol,
                side="buy",
                qty=float(qty),
                limit_price=float(price),
                stop_price=stop_price,
            )
        ),
    )


@when(parsers.parse('I show paper order "{order_id}"'))
def show_paper_order(trading_context, order_id, alpaca_client):
    _record(
        trading_context,
        ShowOrder(_gateway(alpaca_client)).execute(ShowOrderRequest(order_id=order_id)),
    )


@when(parsers.parse('I cancel paper order "{order_id}"'))
def cancel_paper_order(trading_context, order_id, alpaca_client):
    _record(
        trading_context,
        CancelOrder(_gateway(alpaca_client)).execute(
            CancelOrderRequest(order_id=order_id)
        ),
    )


@when("I show the paper balance")
def show_paper_balance(trading_context, alpaca_client):
    _record(
        trading_context,
        ShowBalance(_gateway(alpaca_client)).execute(ShowBalanceRequest()),
    )


@then("the command succeeds")
def command_succeeds(trading_context):
    if trading_context.cli_result is not None:
        assert_that(trading_context.cli_result.exit_code, equal_to(0))
    else:
        assert_that(trading_context.failed, is_(False), trading_context.error)


@then("the positions command fails")
def positions_command_fails(trading_context):
    if trading_context.cli_result is not None:
        assert_that(trading_context.cli_result.exit_code, not_(equal_to(0)))
    else:
        assert_that(trading_context.failed, is_(True))


@then("the command fails")
def command_fails(trading_context):
    if trading_context.cli_result is not None:
        assert_that(trading_context.cli_result.exit_code, not_(equal_to(0)))
    else:
        assert_that(trading_context.failed, is_(True))


@then("the console displays:")
def console_displays_exactly(trading_context, docstring):
    assert_that(trading_context.cli_result, not_none())
    assert_that(trading_context.cli_result.output, equal_to(f"{docstring}\n"))


@then(parsers.parse('the output reports "{message}"'))
def output_reports(trading_context, message):
    assert_that(trading_context.cli_result, not_none())
    assert_that(trading_context.cli_result.output, contains_string(message))


@then("the stored positions are:")
def stored_positions_are(trading_context, datatable):
    rows = _table_rows(datatable)
    positions = trading_context.result.result
    rendered = [
        {
            "symbol": p.symbol,
            "qty": str(p.qty),
            "avg_entry_price": str(p.avg_entry_price),
        }
        for p in positions
    ]
    assert_that(rendered, equal_to(rows))


@then("no paper positions are listed")
def no_paper_positions(trading_context):
    assert_that(trading_context.result.result, equal_to([]))


@then(
    parsers.parse('the created order is for "{symbol}" at {price:f} with stop {stop:f}')
)
def created_order_matches(trading_context, symbol, price, stop):
    order = trading_context.result.result
    assert_that(order.symbol, equal_to(symbol))
    assert_that(order.limit_price, equal_to(price))
    assert_that(order.stop_price, equal_to(stop))


@then(parsers.parse('the stored orders are "{first}" then "{second}"'))
def stored_orders_in_order(trading_context, first, second):
    orders = trading_context.result.result
    assert_that([o.id for o in orders], equal_to([first, second]))


@then(parsers.parse("the shown balance is {equity} equity with {cash} cash"))
def shown_balance_matches(trading_context, equity, cash):
    account = trading_context.result.result
    assert_that(account.equity, equal_to(float(equity)))
    assert_that(account.cash, equal_to(float(cash)))


@then(parsers.parse('the shown order is for "{symbol}" at {price}'))
def shown_order_matches(trading_context, symbol, price):
    order = trading_context.result.result
    assert_that(order.symbol, equal_to(symbol))
    assert_that(order.limit_price, equal_to(float(price)))


@then(parsers.parse('the paper account canceled order "{order_id}"'))
def paper_canceled_order(trading_context, order_id, alpaca_client):
    assert_that(alpaca_client.canceled, equal_to([order_id]))


@then(
    parsers.parse(
        'the paper account received a limit buy for "{symbol}" at {price:f} with stop {stop:f}'
    )
)
def paper_received_buy(trading_context, symbol, price, stop, alpaca_client):
    assert_that(len(alpaca_client.submitted), equal_to(1))
    fields = alpaca_client.submitted[0].to_request_fields()
    assert_that(str(fields.get("symbol")), equal_to(symbol))
    assert_that(float(fields.get("limit_price")), equal_to(price))
    stop_loss = alpaca_client.submitted[0].stop_loss
    assert_that(float(stop_loss.stop_price), equal_to(stop))
