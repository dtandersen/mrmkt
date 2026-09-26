"""Alpaca websocket trade ticks bridged to an async iterator.

The Alpaca stream is callback-based and blocks while running, so each
subscription runs it on a worker thread and forwards trades through an
asyncio queue. Alpaca requires ``async`` handlers, but those run on the
worker's loop, so forwarding still uses ``call_soon_threadsafe`` onto
the subscriber's loop. Stopping the iterator stops the stream and joins
the thread; the thread is daemonic so a stuck join can never hang
shutdown. Session close is scheduled as a task because awaiting it
inside generator teardown is not always legal.
"""

import asyncio
import datetime
import sys
import threading
from collections.abc import AsyncIterator
from pathlib import Path

import yaml

from mrmkt.common.clock import ET
from mrmkt.repo.ticks import LiveTickSource, Tick


def _log_close_result(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    try:
        task.result()
    except Exception as error:
        print(f"tick stream close failed: {error}", file=sys.stderr, flush=True)


class AlpacaTickSource(LiveTickSource):
    """Live trade ticks from an Alpaca data stream (default: IEX feed)."""

    def __init__(self, api_key: str, secret_key: str, feed: str = "iex"):
        self._api_key = api_key
        self._secret_key = secret_key
        self._feed = feed

    @classmethod
    def from_config(cls, feed: str = "iex") -> "AlpacaTickSource":
        """Build from the same alpaca.yaml the CLI watch path uses."""
        config = yaml.safe_load(Path("alpaca.yaml").read_text())
        return cls(config["key"], config["secret"], feed)

    async def subscribe(self, symbol: str) -> AsyncIterator[Tick]:
        from alpaca.data.enums import DataFeed
        from alpaca.data.live import StockDataStream

        queue: asyncio.Queue[Tick] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        async def on_trade(trade) -> None:
            try:
                stamp = getattr(trade, "timestamp", None) or datetime.datetime.now(
                    tz=ET
                )
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=ET)
                tick = Tick(
                    symbol=getattr(trade, "symbol", None) or symbol,
                    price=float(trade.price),
                    at=stamp,
                )
                loop.call_soon_threadsafe(queue.put_nowait, tick)
            except Exception as error:
                print(f"tick handler failed: {error}", file=sys.stderr, flush=True)

        stream = StockDataStream(
            self._api_key, self._secret_key, feed=DataFeed(self._feed)
        )
        stream.subscribe_trades(on_trade, symbol)
        thread = threading.Thread(
            target=stream.run, daemon=True, name=f"mrmkt-ticks-{symbol}"
        )
        thread.start()
        try:
            while True:
                yield await queue.get()
        finally:
            try:
                stream.stop()
            except Exception as error:
                print(f"tick stream stop failed: {error}", file=sys.stderr, flush=True)
            thread.join(timeout=5)
            if thread.is_alive():
                print(
                    f"tick stream thread for {symbol} did not stop",
                    file=sys.stderr,
                    flush=True,
                )
            try:
                closer = loop.create_task(stream.close())
            except RuntimeError as error:
                print(
                    f"tick stream close skipped: {error}", file=sys.stderr, flush=True
                )
            else:
                closer.add_done_callback(_log_close_result)
