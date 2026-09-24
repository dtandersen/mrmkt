from datetime import date
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command import _shared as shared
from mrmkt.common.clock import ClockStub
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "indicators.feature"
scenarios(str(FEATURE))


@pytest.fixture
def indicator_context(monkeypatch):
    clock = ClockStub()
    clock.set_time(date(2024, 1, 31))
    context = SimpleNamespace(
        local=InMemoryFinancialRepository(),
        clock=clock,
        result=None,
    )
    monkeypatch.setattr(
        shared,
        "create_local_ticker_repository",
        lambda: (context.local, lambda: None),
    )
    monkeypatch.setattr(shared, "create_clock", lambda: context.clock)
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the local price catalog contains these daily bars:")
def add_local_price_bars(indicator_context, datatable):
    for row in _table_rows(datatable):
        close = float(row["close"])
        indicator_context.local.add_price(
            StockPrice(
                symbol=row["symbol"],
                date=date.fromisoformat(row["date"]),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=0.0,
            )
        )


@given(parsers.parse('the fake clock says today is "{today}"'))
def fake_clock_says_today(indicator_context, today):
    indicator_context.clock.set_time(date.fromisoformat(today))


@when(parsers.parse('I execute "{command}"'))
def execute_indicator_command(indicator_context, command):
    args = split(command)
    indicator_context.result = CliRunner().invoke(cli.app, args[1:])


@then("the command succeeds")
def indicator_command_succeeds(indicator_context):
    assert indicator_context.result.exit_code == 0, indicator_context.result.output


@then(parsers.parse('the indicator output has column "{column}" and these values:'))
def indicator_output_contains_values(indicator_context, column, datatable):
    expected = [
        f"{row['date']} | {float(row['close']):g} | {float(row['value']):g}"
        for row in _table_rows(datatable)
    ]
    lines = indicator_context.result.output.splitlines()
    assert lines[0] == f"DATE | CLOSE | {column}"
    assert lines[1:] == expected


@then(parsers.parse('the indicator output has columns "{low}" and "{high}" and these values:'))
def indicator_output_contains_pair_values(indicator_context, low, high, datatable):
    expected = [
        f"{row['date']} | {float(row['close']):g} | {float(row['low']):g} | {float(row['high']):g}"
        for row in _table_rows(datatable)
    ]
    lines = indicator_context.result.output.splitlines()
    assert lines[0] == f"DATE | CLOSE | {low} | {high}"
    assert lines[1:] == expected
