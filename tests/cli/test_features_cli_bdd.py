"""Thin CLI coverage for the feature commands (argument passing)."""

import datetime
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.common.clock import ClockStub
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker

scenarios(str(Path(__file__).parent.parent / "features" / "cli" / "features.feature"))


@pytest.fixture
def feature_cli_context(financial_repository):
    clock = ClockStub()
    clock.set_time(datetime.date(2026, 9, 27))
    context = SimpleNamespace(clock=clock, result=None)
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        clock=context.clock,
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the ticker catalog contains:")
def seed_tickers(feature_cli_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@when(parsers.parse('I execute "{command}"'))
def execute(feature_cli_context, command):
    feature_cli_context.result = CliRunner().invoke(
        cli.app, split(command)[1:], obj=feature_cli_context.deps
    )


@then("the command succeeds")
def succeeds(feature_cli_context):
    assert_that(feature_cli_context.result.exit_code, equal_to(0))


@then("the command fails")
def fails(feature_cli_context):
    assert_that(feature_cli_context.result.exit_code != 0, equal_to(True))


@then(parsers.parse('the output contains "{text}"'))
def output_contains(feature_cli_context, text):
    assert_that(feature_cli_context.result.output, contains_string(text))
