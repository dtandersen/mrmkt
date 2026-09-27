"""Gateway tests for the RabbitMQ transport (hand-rolled pika doubles)."""

import json
from datetime import UTC, datetime

from hamcrest import assert_that, equal_to

from mrmkt.command.watch import Quote
from mrmkt.composition import rabbitmq_url_from_section
from mrmkt.ext.rabbitmq import RabbitMQMessageQueue


class FakePikaChannel:
    def __init__(self):
        self.declared = []
        self.published = []
        self.consumers = {}
        self.inbound = {}
        self.consuming_started = False

    def queue_declare(self, queue, durable=True):
        self.declared.append((queue, durable))

    def basic_publish(self, exchange, routing_key, body):
        self.published.append((exchange, routing_key, body))

    def basic_consume(self, queue, on_message_callback, auto_ack=True):
        self.consumers[queue] = on_message_callback

    def start_consuming(self):
        self.consuming_started = True
        for queue, bodies in self.inbound.items():
            for body in bodies:
                self.consumers[queue](self, None, None, body)


class FakePikaConnection:
    def __init__(self):
        self.channel_obj = FakePikaChannel()
        self.closed = False

    def channel(self):
        return self.channel_obj

    def close(self):
        self.closed = True


MOMENT = datetime(2022, 4, 4, 14, 0, tzinfo=UTC)


def make_queue(connection):
    return RabbitMQMessageQueue("amqp://test", connect=lambda: connection)


def test_subscribe_declares_consumes_and_dispatches_quotes():
    connection = FakePikaConnection()
    queue = make_queue(connection)
    body = json.dumps(
        {
            "symbol": "AAA",
            "bid": 106.0,
            "ask": 107.0,
            "timestamp": MOMENT.isoformat(),
        }
    ).encode("utf-8")
    connection.channel_obj.inbound["subscribe.realtime.price"] = [body]
    received = []
    queue.subscribe("subscribe.realtime.price", on_event=received.append)
    assert_that(
        connection.channel_obj.declared, equal_to([("subscribe.realtime.price", True)])
    )
    assert_that(connection.channel_obj.consuming_started, equal_to(True))
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.0, ask=107.0, timestamp=MOMENT)]),
    )


def test_publish_declares_and_posts_json_then_closes():
    connection = FakePikaConnection()
    queue = make_queue(connection)
    queue.publish(
        "subscribe.realtime.price.AAA",
        Quote(symbol="AAA", bid=106.0, ask=107.0, timestamp=MOMENT),
    )
    assert_that(
        connection.channel_obj.declared,
        equal_to([("subscribe.realtime.price.AAA", True)]),
    )
    (exchange, routing_key, body) = connection.channel_obj.published[0]
    assert_that(exchange, equal_to(""))
    assert_that(routing_key, equal_to("subscribe.realtime.price.AAA"))
    assert_that(
        json.loads(body),
        equal_to(
            {
                "symbol": "AAA",
                "bid": 106.0,
                "ask": 107.0,
                "timestamp": MOMENT.isoformat(),
            }
        ),
    )
    assert_that(connection.closed, equal_to(True))


def test_poison_message_is_skipped_without_killing_consumption():
    import io
    from contextlib import redirect_stderr

    connection = FakePikaConnection()
    queue = make_queue(connection)
    good = json.dumps(
        {
            "symbol": "AAA",
            "bid": 106.0,
            "ask": 107.0,
            "timestamp": MOMENT.isoformat(),
        }
    ).encode("utf-8")
    connection.channel_obj.inbound["subscribe.realtime.price"] = [b"not-json", good]
    received = []
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        queue.subscribe("subscribe.realtime.price", on_event=received.append)
    assert_that(
        received,
        equal_to([Quote(symbol="AAA", bid=106.0, ask=107.0, timestamp=MOMENT)]),
    )
    assert_that("skipped" in stderr.getvalue(), equal_to(True))


def test_rabbitmq_url_defaults_match_docker_compose():
    assert_that(
        rabbitmq_url_from_section({}),
        equal_to("amqp://mrmkt:mrmkt@localhost:5672/"),
    )


def test_rabbitmq_url_uses_config_section_and_quotes_password():
    assert_that(
        rabbitmq_url_from_section(
            {
                "user": "svc",
                "password": "p@ss/word",
                "host": "rabbitmq",
                "port": 5673,
            }
        ),
        equal_to("amqp://svc:p%40ss%2Fword@rabbitmq:5673/"),
    )
