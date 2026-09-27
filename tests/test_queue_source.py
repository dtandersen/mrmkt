"""Adapter tests: queue subjects feed WatchPrices through PriceSource."""

from datetime import UTC, datetime

from hamcrest import assert_that, contains_string, equal_to, not_
from tests.fakes import CapturingLog, FakeMessageQueue

from mrmkt.command.start_engine import DEFAULT_SUBJECT
from mrmkt.composition import QueuePriceSource, rabbitmq_display_address
from mrmkt.gateway import Quote


def test_queue_source_subscribes_per_symbol_and_forwards_quotes():
    queue = FakeMessageQueue()
    received = []
    log = CapturingLog()
    source = QueuePriceSource(queue, log)
    source.subscribe(["AAA"], "iex", on_quote=received.append)
    assert_that(
        log.lines,
        equal_to(["Connecting to price queue", "Subscribing to AAA"]),
    )
    assert_that(queue.subjects, equal_to([f"{DEFAULT_SUBJECT}.AAA"]))
    quote = Quote(
        symbol="AAA",
        bid=106.0,
        ask=107.0,
        timestamp=datetime(2022, 4, 4, 14, 0, tzinfo=UTC),
    )
    queue.deliver(f"{DEFAULT_SUBJECT}.AAA", quote)
    assert_that(received, equal_to([quote]))


def test_queue_source_names_the_broker_address():
    log = CapturingLog()
    source = QueuePriceSource(FakeMessageQueue(), log, address="RabbitMQ@broker:5672")
    source.subscribe(["AAA"], "iex", on_quote=lambda quote: None)

    assert_that(
        log.lines,
        equal_to(["Connecting to RabbitMQ@broker:5672", "Subscribing to AAA"]),
    )


def test_broker_label_strips_credentials():
    label = rabbitmq_display_address("amqp://mrmkt:s3cret@broker:5672/")

    assert_that(label, equal_to("RabbitMQ@broker:5672"))
    assert_that(label, not_(contains_string("s3cret")))
