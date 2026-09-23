"""Alpaca websocket source for risk-range alerts (trades + daily bars)."""

from mrmkt.usecase.alerts import ET


class AlpacaStreamSource:
    """Wire an Alpaca data stream into an AlertEngine.

    Trade ticks drive transitions; daily-bar updates roll new closes
    into per-symbol history so levels recompute on strictly newer bars
    (same-day bar updates are ignored by the engine). The stream object
    is injected, so tests can substitute a recording stub.
    """

    def __init__(self, stream, engine, clock_now):
        self.stream = stream
        self.engine = engine
        self.clock_now = clock_now

    def start(self, symbols: list[str]) -> None:
        """Subscribe and block on the stream (returns on disconnect)."""
        self.stream.subscribe_trades(self._on_trade, *symbols)
        self.stream.subscribe_daily_bars(self._on_bar, *symbols)
        self.stream.run()

    def _on_trade(self, trade) -> None:
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
            self.engine.on_tick(trade.symbol, float(trade.price), stamp)
        except Exception as error:
            # Never let a bad tick kill the stream; report and continue.
            print(f"alert trade handler failed: {error}", file=sys.stderr, flush=True)

    def _on_bar(self, bar) -> None:
        import sys

        try:
            stamp = bar.timestamp
            if stamp is not None and stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=ET)
            bar_date = stamp.astimezone(ET).date() if stamp is not None else None
            self.engine.roll_daily_bar(bar.symbol, float(bar.close), bar_date)
        except Exception as error:
            print(f"alert bar handler failed: {error}", file=sys.stderr, flush=True)
