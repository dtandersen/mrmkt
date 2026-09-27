"""Start the engine: attach to the queue's realtime price events."""

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.watch import Quote

DEFAULT_SUBJECT = "subscribe.realtime.price"


class MessageQueue(ABC):
    """Queue transport for realtime price events."""

    @abstractmethod
    def subscribe(self, subject: str) -> None:
        """Attach to the subject."""

    @abstractmethod
    def publish(self, subject: str, event: Quote) -> None:
        """Broadcast one price event to the subject's consumers."""


class PriceProvider(ABC):
    """Push source of live quotes; the Alpaca websocket in prod."""

    @abstractmethod
    def subscribe(
        self, symbols: list[str], *, on_quote: Callable[[Quote], None]
    ) -> None:
        """Attach, push each quote to the handler, and block.

        Must not return while the stream is alive: worker threads live
        inside this call, so a register-and-return implementation would
        silently end streaming. Ends on close/KeyboardInterrupt.
        """


@dataclass(frozen=True)
class StartEngineRequest:
    subject: str = DEFAULT_SUBJECT


@dataclass
class StartEngineResult(BaseResult[None]):
    pass


class StartEngine(Command[StartEngineRequest, StartEngineResult]):
    """Attach the engine to the queue; stream symbols on worker threads."""

    def __init__(
        self,
        queue: MessageQueue,
        prices: PriceProvider,
        engine_thread: Callable = threading.Thread,
    ):
        self.queue = queue
        self.prices = prices
        self.spawn_thread = engine_thread
        self.subject = DEFAULT_SUBJECT
        self.workers = {}
        self.stop_event = threading.Event()

    def execute(self, request: StartEngineRequest) -> StartEngineResult:
        self.subject = request.subject
        self.queue.subscribe(request.subject)

        return StartEngineResult.success(None)

    def stop(self) -> None:
        """Signal all worker threads to stop; loops honor the event."""
        self.stop_event.set()

    def subscribe_symbol(self, symbol: str) -> None:
        """Start streaming one symbol's price events on a new thread."""
        if symbol in self.workers:
            return
        worker = self.spawn_thread(
            target=self._stream_symbol, args=(symbol,), daemon=True
        )
        self.workers[symbol] = worker
        worker.start()

    def _stream_symbol(self, symbol: str) -> None:
        channel = f"{self.subject}.{symbol}"

        def handle_quote(quote: Quote) -> None:
            print(
                f"{quote.timestamp.isoformat()} | {quote.symbol} | "
                f"bid {quote.bid:g} ask {quote.ask:g} -> {channel}",
                flush=True,
            )
            self.queue.publish(channel, quote)

        self.prices.subscribe([symbol], on_quote=handle_quote)
