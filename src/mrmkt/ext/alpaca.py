from typing import Any

from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.trading.requests import GetAssetsRequest

from mrmkt.entity.ticker import Ticker
from mrmkt.repo.tickers import ReadOnlyTickerRepository


class AlpacaTickerRepository(ReadOnlyTickerRepository):
    """Read active, tradable Alpaca US equities as MrMkt tickers.

    Alpaca provides an asset class but not a stock-versus-ETF subtype. Store
    the class value in the existing ticker ``type`` field rather than guessing.
    """

    def __init__(self, trading_client: Any):
        self.trading_client = trading_client

    def get_tickers(self) -> list[Ticker]:
        request = GetAssetsRequest(
            asset_class=AssetClass.US_EQUITY,
            status=AssetStatus.ACTIVE,
        )
        assets = self.trading_client.get_all_assets(filter=request)

        tickers = []
        for asset in assets:
            asset_class = self._value(asset.asset_class)
            status = self._value(asset.status)
            if asset_class != AssetClass.US_EQUITY.value:
                continue
            if status != AssetStatus.ACTIVE.value or not asset.tradable:
                continue

            tickers.append(
                Ticker(
                    ticker=asset.symbol,
                    exchange=self._value(asset.exchange),
                    type=asset_class,
                )
            )

        return sorted(tickers, key=lambda ticker: (ticker.ticker, ticker.exchange))

    def get_symbols(self) -> list[str]:
        return [ticker.ticker for ticker in self.get_tickers()]

    @staticmethod
    def _value(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)
