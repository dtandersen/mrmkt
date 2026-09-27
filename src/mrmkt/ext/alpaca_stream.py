"""Alpaca websocket source for risk-range alerts (trades + daily bars)."""

from collections.abc import Callable

from mrmkt.command.watch import BarUpdate, PriceTick
from mrmkt.common.clock import ET


class AlpacaStreamSource:
    """Live price transport: subscribes to symbols, emits normalized updates.

    Trade ticks and daily-bar updates arrive as raw Alpaca objects and are
    normalized here to :class:`PriceTick` / :class:`BarUpdate` before
    reaching the trigger analyzer. The source never sees the analyzer;
    WatchPrices maps each update onto it. The stream object is injected,
    so tests can substitute a recording stub.
    """

    def __init__(self, stream, clock_now):
        self.stream = stream
        self.clock_now = clock_now

    def subscribe(
        self,
        symbols: list[str],
        on_trade: Callable[[PriceTick], None],
        on_bar: Callable[[BarUpdate], None],
    ) -> None:
        """Subscribe and block on the stream (returns on disconnect)."""
        self.stream.subscribe_trades(
            lambda trade: self._handle_trade(trade, on_trade), *symbols
        )
        self.stream.subscribe_daily_bars(
            lambda bar: self._handle_bar(bar, on_bar), *symbols
        )
        self.stream.run()

    def _handle_trade(self, trade, on_trade: Callable[[PriceTick], None]) -> None:
        import sys

        try:
            # Prefer the exchange print timestamp for session
            # classification: receipt-time clock_now() can misclassify
            # delayed prints around open/close. The injected clock is only
            # a fallback when the trade carries no timestamp.
            stamp = getattr(trade, "timestamp", None)
            if stamp is None:
                stamp = self.clock_now()
            elif stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=ET)
            on_trade(
                PriceTick(symbol=trade.symbol, price=float(trade.price), moment=stamp)
            )
        except Exception as error:
            # Never let a bad tick kill the stream; report and continue.
            print(f"alert trade handler failed: {error}", file=sys.stderr, flush=True)

    def _handle_bar(self, bar, on_bar: Callable[[BarUpdate], None]) -> None:
        import sys

        try:
            stamp = bar.timestamp
            if stamp is not None and stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=ET)
            bar_date = stamp.astimezone(ET).date() if stamp is not None else None
            on_bar(
                BarUpdate(symbol=bar.symbol, close=float(bar.close), bar_date=bar_date)
            )
        except Exception as error:
            print(f"alert bar handler failed: {error}", file=sys.stderr, flush=True)
