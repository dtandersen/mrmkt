"""Adapter tests: queue subjects feed WatchPrices through PriceSource."""

from datetime import UTC, datetime

from hamcrest import assert_that, equal_to
from tests.fakes import FakeMessageQueue

from mrmkt.command.start_engine import DEFAULT_SUBJECT
from mrmkt.command.watch import Quote
from mrmkt.composition import QueuePriceSource


def test_queue_source_subscribes_per_symbol_and_forwards_quotes():
    queue = FakeMessageQueue()
    received = []
    source = QueuePriceSource(queue)
    source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(queue.subjects, equal_to([f"{DEFAULT_SUBJECT}.AAA"]))
    quote = Quote(
        symbol="AAA",
        bid=106.0,
        ask=107.0,
        timestamp=datetime(2022, 4, 4, 14, 0, tzinfo=UTC),
    )
    queue.deliver(f"{DEFAULT_SUBJECT}.AAA", quote)
    assert_that(received, equal_to([quote]))
