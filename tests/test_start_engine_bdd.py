"""BDD coverage for starting the queue-driven engine."""

from datetime import datetime
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to, not_none
from pytest_bdd import given, parsers, scenarios, then, when
from tests.fakes import FakePriceSource

from mrmkt.command.start_engine import StartEngine, StartEngineRequest
from mrmkt.command.watch import Quote

scenarios("features/command/start_engine.feature")


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


# Timestamp used when a price-data table says "?": the scenario never asserts
# on it, so any fixed value keeps Quote's non-optional timestamp satisfied.
ANY_TIMESTAMP = datetime(2022, 1, 1)


class FakeThread:
    """Test thread: runs the target inline instead of spawning."""

    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args
        self.started = False

    def start(self) -> None:
        self.started = True
        self.target(*self.args)


@pytest.fixture
def engine_context():
    return SimpleNamespace(
        result=None,
        engine=None,
        prices=FakePriceSource(),
    )


def _start(engine_context, fake_queue):
    engine = StartEngine(fake_queue, engine_context.prices, spawn_thread=FakeThread)
    engine_context.engine = engine
    fake_queue.on_message = engine.subscribe_symbol
    run_engine = engine.execute
    engine_context.result = run_engine(StartEngineRequest())


@given("the engine is started")
def engine_is_started(engine_context, fake_queue):
    _start(engine_context, fake_queue)


@when("the engine starts")
def engine_starts(engine_context, fake_queue):
    _start(engine_context, fake_queue)


@given("the price data:")
def price_data(engine_context, datatable):
    engine_context.prices.quotes = [
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
