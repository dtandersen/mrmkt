"""Blocking watch driver for the SIGINT test (no network).

Reads nothing, connects nowhere: price history is canned in-memory and the
stream runner blocks on an event forever, so the parent test can deliver a
real SIGINT mid-watch and assert graceful shutdown.
"""

import threading
from datetime import date, timedelta

from mrmkt.command.watch import WatchPrices, WatchPricesRequest
from mrmkt.common.clock import ClockStub
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.ext.backend import InMemoryBackend

START = date(2022, 1, 3)
N_BARS = 60


def main() -> None:
    repository = InMemoryBackend()
    repository.add_ticker(Ticker(ticker="AAA", exchange="NASDAQ", type="us_equity"))
    closes = [100.0 * (1.002**i) for i in range(N_BARS)]
    day = START
    added = 0
    while added < N_BARS:
        if day.weekday() < 5:
            close = closes[added]
            repository.add_price(
                StockPrice(
                    symbol="AAA",
                    date=day,
                    open=close,
                    high=close * 1.005,
                    low=close * 0.995,
                    close=close,
                    volume=1000.0,
                )
            )
            added += 1
        day += timedelta(days=1)
    clock = ClockStub()
    clock.set_time(date(2022, 4, 1))
    gate = threading.Event()

    def emit(line: str, err: bool = False) -> None:
        print(line, flush=True)

    command = WatchPrices(repository, clock, lambda s, e, f: gate.wait(), emit)
    command.execute(WatchPricesRequest(symbols=["AAA"]))


if __name__ == "__main__":
    main()
