"""Shared test doubles."""

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace

from alpaca.trading.enums import AssetClass, AssetStatus

from mrmkt.repo.ticks import LiveTickSource, Tick


class FakeAlpacaClient:
    def __init__(self):
        self.assets = []
        self.error = None

    def get_all_assets(self, filter=None):
        if self.error is not None:
            raise self.error
        return self.assets

    def set_assets(self, rows):
        """Populate the fake catalog from row dicts with symbol/exchange/asset_class/status/tradable."""
        self.assets = [
            SimpleNamespace(
                symbol=row["symbol"],
                exchange=row["exchange"],
                asset_class=AssetClass(row["asset_class"]),
                status=AssetStatus(row["status"]),
                tradable=row["tradable"].lower() == "true",
            )
            for row in rows
        ]


class FakeTickSource(LiveTickSource):
    """Scripted live ticks; holds the stream open after scripts run dry."""

    def __init__(self):
        self._ticks = []

    def add_tick(self, symbol, price, at):
        self._ticks.append(Tick(symbol=symbol, price=price, at=at))

    async def subscribe(self, symbol: str) -> AsyncIterator[Tick]:
        for tick in [tick for tick in self._ticks if tick.symbol == symbol]:
            yield tick
        await asyncio.Event().wait()
