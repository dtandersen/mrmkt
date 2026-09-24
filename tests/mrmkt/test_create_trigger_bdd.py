"""BDD coverage for trigger create/list/enable/disable/remove paths."""

from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli as cli
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "mrmkt" / "create_trigger.feature"
scenarios(str(FEATURE))


@pytest.fixture
def trigger_context(monkeypatch):
    context = SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
    )
    monkeypatch.setattr(
        cli,
        "create_local_ticker_repository",
        lambda: (context.local, lambda: None),
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the trigger catalog contains these symbols:")
def trigger_catalog_contains_symbols(trigger_context, datatable):
    for row in _table_rows(datatable):
        trigger_context.local.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@when(parsers.parse('I execute "{command}"'))
def execute_trigger_command(trigger_context, command):
    args = split(command)
    trigger_context.result = CliRunner().invoke(cli.app, args[1:])


@then("the command succeeds")
def trigger_command_succeeds(trigger_context):
    assert trigger_context.result.exit_code == 0, trigger_context.result.output


@then("the command fails")
def trigger_command_fails(trigger_context):
    assert trigger_context.result.exit_code != 0, trigger_context.result.output


@then(parsers.parse('the output mentions "{text}"'))
def trigger_output_mentions(trigger_context, text):
    output = trigger_context.result.output
    stderr = getattr(trigger_context.result, "stderr", "") or ""
    assert text in output or text in stderr, output
