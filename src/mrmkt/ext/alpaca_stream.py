"""Alpaca websocket source for best-bid/ask quote updates."""

from collections.abc import Callable

from mrmkt.command.base import Log
from mrmkt.command.watch import Quote
from mrmkt.common.clock import ET


class AlpacaStreamSource:
    """Normalize Alpaca quote messages before forwarding them to the watcher."""

    def __init__(self, stream, clock_now, log: Log):
        self.stream = stream
        self.clock_now = clock_now
        self.log = log

    def subscribe(
        self,
        symbols: list[str],
        on_quote: Callable[[Quote], None],
    ) -> None:
        """Subscribe to quotes and block on the stream."""

        async def handle_quote(quote) -> None:
            self._handle_quote(quote, on_quote)

        self.log("Connected to Alpaca stream")
        self.log(f"Subscribing to {', '.join(symbols)}")
        self.stream.subscribe_quotes(handle_quote, *symbols)
        self.stream.run()

    def _handle_quote(self, quote, on_quote: Callable[[Quote], None]) -> None:
        import sys

        try:
            stamp = getattr(quote, "timestamp", None)
            if stamp is None:
                stamp = self.clock_now()
            elif stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=ET)
            on_quote(
                Quote(
                    symbol=quote.symbol,
                    bid=float(quote.bid_price),
                    ask=float(quote.ask_price),
                    timestamp=stamp,
                )
            )
        except Exception as error:
            # Never let a bad quote kill the stream; report and continue.
            print(f"alert quote handler failed: {error}", file=sys.stderr, flush=True)
