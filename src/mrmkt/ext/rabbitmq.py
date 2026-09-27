"""RabbitMQ transport for realtime price events (pika, blocking).

One connection serves the blocking control subscription; each publish
opens its own short-lived connection because pika connections must not
be shared across threads (workers publish concurrently).
"""

import json
from datetime import datetime
from urllib.parse import urlsplit

import pika

from mrmkt.command.start_engine import MessageQueue
from mrmkt.command.watch import Quote


class RabbitMQMessageQueue(MessageQueue):
    """MessageQueue over a RabbitMQ broker (default: local dev instance)."""

    def __init__(self, url: str, connect=None, log=None):
        self.url = url
        self.log = log
        self._connect = connect or (
            lambda: pika.BlockingConnection(pika.URLParameters(url))
        )

    def subscribe(self, subject: str, *, on_event) -> None:
        if self.log is not None:
            host = urlsplit(self.url).hostname or "unknown"
            self.log(f"Connecting to RabbitMQ@{host}")
        connection = self._connect()
        channel = connection.channel()
        channel.queue_declare(queue=subject, durable=True)
        if self.log is not None:
            self.log(f"Subscribing to {subject}")
        channel.basic_consume(
            queue=subject,
            on_message_callback=lambda ch, method, properties, body: self._dispatch(
                body, on_event
            ),
            auto_ack=True,
        )
        channel.start_consuming()

    def publish(self, subject: str, event: Quote) -> None:
        connection = self._connect()
        try:
            channel = connection.channel()
            channel.queue_declare(queue=subject, durable=True)
            channel.basic_publish(
                exchange="", routing_key=subject, body=self._encode(event)
            )
        finally:
            connection.close()

    def _dispatch(self, body: bytes, on_event) -> None:
        import sys

        try:
            data = json.loads(body)
            on_event(
                Quote(
                    symbol=data["symbol"],
                    bid=float(data["bid"]),
                    ask=float(data["ask"]),
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                )
            )
        except (ValueError, KeyError, TypeError) as error:
            # Never let a bad message kill the stream; report and continue.
            print(f"rabbitmq message skipped: {error}", file=sys.stderr, flush=True)

    @staticmethod
    def _encode(event: Quote) -> bytes:
        return json.dumps(
            {
                "symbol": event.symbol,
                "bid": event.bid,
                "ask": event.ask,
                "timestamp": event.timestamp.isoformat(),
            }
        ).encode("utf-8")
