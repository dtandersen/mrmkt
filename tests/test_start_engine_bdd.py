"""BDD coverage for starting the queue-driven engine."""

from datetime import datetime
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to, not_none
from pytest_bdd import given, parsers, scenarios, then, when
from tests.fakes import CapturingConsole, CapturingLog, FakePriceSource
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.start_engine import StartEngine, StartEngineRequest
from mrmkt.command.watch import Quote
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.trigger import Trigger

scenarios(
    "features/cli/start_engine.feature",
    "features/command/start_engine.feature",
)


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


# Timestamp used when a price-data table says "?": the scenario never asserts
# on it, so any fixed value keeps Quote's non-optional timestamp satisfied.
ANY_TIMESTAMP = datetime(2022, 1, 1)


class FakeThread:
    """Test worker: runs the target inline on construction, no spawning."""

    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args
        self.started = True
        self.target(*self.args)


@pytest.fixture
def engine_context(fake_queue, financial_repository):
    prices = FakePriceSource()
    console = CapturingConsole()
    log = CapturingLog()
    context = SimpleNamespace(
        result=None,
        cli_result=None,
        engine=None,
        prices=prices,
        console=console,
        log=log,
    )
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        engine_queue=fake_queue,
        engine_prices=prices,
        log=log,
    )
    return context


def _start(engine_context, fake_queue, financial_repository):
    engine = StartEngine(
        financial_repository,
        fake_queue,
        engine_context.prices,
        engine_context.console,
        engine_context.log,
        engine_thread=FakeThread,
    )
    engine_context.engine = engine
    run_engine = engine.execute
    engine_context.result = run_engine(StartEngineRequest())


@given(parsers.parse('stored trigger "{name}" for "{symbol}"'))
def stored_trigger_for_symbol(engine_context, financial_repository, name, symbol):
    financial_repository.add_trigger(
        Trigger(id=None, name=name, symbol=symbol, indicator="risk-range")
    )


@given("the engine is started")
def engine_is_started(engine_context, fake_queue, financial_repository):
    _start(engine_context, fake_queue, financial_repository)


@when(parsers.parse('I execute "{command}"'))
def execute_engine_command(engine_context, command):
    args = split(command)
    engine_context.cli_result = CliRunner().invoke(
        cli.app, args[1:], obj=engine_context.deps
    )


@then("the command succeeds")
def command_succeeds(engine_context):
    assert_that(engine_context.cli_result.exit_code, equal_to(0))


@then(parsers.parse('the queue is subscribed to "{subject}"'))
def queue_subscribed(engine_context, fake_queue, subject):
    assert_that(fake_queue.subjects, equal_to([subject]))


@when("the engine starts")
def engine_starts(engine_context, fake_queue, financial_repository):
    _start(engine_context, fake_queue, financial_repository)


@given("the price data:")
def price_data_available(engine_context):
    """Declare market data is available; rows arrive through pushes."""


@when(parsers.parse("the price provider pushes:"))
def price_provider_pushes(engine_context, datatable):
    engine_context.prices.push(
        [
            Quote(
                symbol=row["symbol"],
                bid=float(row["bid"]),
                ask=float(row["ask"]),
                timestamp=ANY_TIMESTAMP
                if row["timestamp"].strip() == "?"
                else datetime.fromisoformat(row["timestamp"]),
            )
            for row in _table_rows(datatable)
        ]
    )


@when(parsers.parse('the message "{subject}" for "{symbol}" is sent'))
def subscription_message_sent(engine_context, fake_queue, subject, symbol):
    fake_queue.send(subject, symbol)


@then(parsers.parse('the engine is subscribed to "{subject}" events'))
def engine_subscribed(engine_context, fake_queue, subject):
    assert_that(engine_context.result.is_success(), equal_to(True))
    assert_that(fake_queue.subjects, equal_to([subject]))


@then(
    parsers.parse(
        "the engine starts streaming stock price data for {symbol} on a new thread"
    )
)
def engine_streams_symbol(engine_context, symbol):
    worker = engine_context.engine.workers.get(symbol)
    assert_that(worker, not_none())
    assert_that(worker.started, equal_to(True))


@then(parsers.parse('the price data is sent to the "{subject}" channel:'))
def price_data_sent_to_channel(engine_context, fake_queue, subject, datatable):
    expected = [
        (row["symbol"], float(row["bid"]), float(row["ask"]))
        for row in _table_rows(datatable)
    ]
    actual = [
        (event.symbol, event.bid, event.ask)
        for channel, event in fake_queue.published
        if channel == subject
    ]
    assert_that(actual, equal_to(expected))
