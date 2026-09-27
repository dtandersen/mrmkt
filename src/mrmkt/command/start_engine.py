"""Start the engine: attach to the queue's realtime price events."""

import threading
from collections.abc import Callable
from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command, Console, Log
from mrmkt.gateway import MessageQueue, PriceProvider, Quote

DEFAULT_SUBJECT = "subscribe.realtime.price"


def _spawn_worker(target, args=(), daemon=None):
    """Construct and start a daemon worker thread."""
    worker = threading.Thread(target=target, args=args, daemon=daemon)
    worker.start()
    return worker


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
        repository,
        queue: MessageQueue,
        prices: PriceProvider,
        console: Console,
        log: Log,
        engine_thread: Callable = _spawn_worker,
    ):
        self.repository = repository
        self.queue = queue
        self.prices = prices
        self.console = console
        self.log = log
        self.spawn_thread = engine_thread
        self.subject = DEFAULT_SUBJECT
        self.workers = {}
        self.stop_event = threading.Event()

    def execute(self, request: StartEngineRequest) -> StartEngineResult:
        try:
            self.console(f"Engine starting: subscribing to {request.subject}")
            self.subject = request.subject
            for symbol in self._enabled_symbols():
                self.subscribe_symbol(symbol)
            self.queue.subscribe(request.subject, on_event=self.subscribe_symbol)
        except KeyboardInterrupt:
            self.console("Engine stopped.")
        except Exception as error:
            self.log(f"Failed to start engine: {error}")
            return StartEngineResult.error([f"Failed to start engine: {error}"])
        return StartEngineResult.success(None)

    def stop(self) -> None:
        """Signal all worker threads to stop; loops honor the event."""
        self.stop_event.set()

    def _enabled_symbols(self) -> list[str]:
        """Symbols with enabled stored triggers, deduplicated."""
        seen: list[str] = []
        for trigger in self.repository.list_triggers(enabled_only=True):
            if trigger.symbol not in seen:
                seen.append(trigger.symbol)
        return sorted(seen)

    def subscribe_symbol(self, symbol: str) -> None:
        """Start streaming one symbol's price events on a new thread."""
        if symbol in self.workers:
            return
        self.workers[symbol] = self.spawn_thread(
            target=self._stream_symbol, args=(symbol,), daemon=True
        )

    def _stream_symbol(self, symbol: str) -> None:
        channel = f"{self.subject}.{symbol}"

        def handle_quote(quote: Quote) -> None:
            self.log(
                f"{quote.timestamp.isoformat()} | {quote.symbol} | "
                f"bid {quote.bid:g} ask {quote.ask:g} -> {channel}"
            )
            self.queue.publish(channel, quote)

        self.log(f"Engine streaming {symbol} -> {channel}")
        self.prices.subscribe([symbol], on_quote=handle_quote)
