"""Shared test doubles."""

from types import SimpleNamespace

from alpaca.trading.enums import AssetClass, AssetStatus


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
