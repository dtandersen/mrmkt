"""Scripting facade for user-scripts: ``mrmkt.connect()``.

Outer layer like the CLI: thin wrappers over commands from the shared
``CommandFactory``. ``connect()`` uses the same default configuration
as the CLI; pass ``backend=`` to override ``MRMKT_BACKEND``. Tests
wrap an ``AppContext`` directly instead of calling ``connect()``.
"""

from mrmkt.command._shared import normalize_tag
from mrmkt.command.base import BaseResult, Status
from mrmkt.command.list_prices import ListPricesRequest
from mrmkt.command.list_symbols import ListSymbolsRequest
from mrmkt.composition import AppContext, create_app_context
from mrmkt.entity.stock_price import StockPrice


def _check[T](result: BaseResult[T], *, what: str) -> T:
    """Unwrap a command result, raising scripting-friendly errors."""
    if result.status is Status.SUCCESS:
        if result.result is None:
            raise RuntimeError(f"{what}: empty result")
        return result.result
    detail = "; ".join(result.errors) or result.status.name
    if result.status is Status.NOT_FOUND:
        raise LookupError(f"{what}: {detail}")
    if result.status is Status.INVALID_DATA:
        raise ValueError(f"{what}: {detail}")
    raise RuntimeError(f"{what}: {detail}")


class PricesAccessor:
    """Settled daily bars, oldest first."""

    def __init__(self, factory):
        self._factory = factory

    def of_symbol(
        self,
        symbol: str,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[StockPrice]:
        """List stored bars for one symbol, oldest first."""
        result = self._factory.list_prices().execute(
            ListPricesRequest(symbols=[symbol], from_date=from_date, to_date=to_date)
        )
        return _check(result, what=f"prices for {symbol}")

    def latest(self, symbol: str) -> StockPrice:
        """Most recent stored bar for one symbol."""
        bars = self.of_symbol(symbol)
        if not bars:
            raise LookupError(f"no stored prices for {symbol}")
        return bars[-1]

    def import_history(
        self,
        symbols: list[str],
        *,
        provider: str = "alpaca",
        from_date: str,
        to_date: str | None = None,
    ) -> int:
        """Fetch bars into the store; returns the new-bar count."""
        from mrmkt.command.import_prices import ImportPricesRequest

        checked = provider.strip().lower()
        if checked not in ("alpaca", "tiingo"):
            raise ValueError(f"unknown price provider {provider!r}")
        result = self._factory.import_prices(provider=checked).execute(
            ImportPricesRequest(
                provider=checked,
                symbols=list(symbols),
                from_date=from_date,
                to_date=to_date,
            )
        )
        outcome = _check(result, what=f"price import for {symbols}")
        return outcome.result.imported


class RealtimeAccessor:
    """Live quotes off the bus: ``mkt.prices_realtime.latest("SPY")``.

    Read-only: needs the engine publishing (see architecture constraint
    in moneyman memory). Raises LookupError when nothing flows in time.
    Persisting ticks needs its own table — not this accessor.
    """

    def __init__(self, factory):
        self._factory = factory

    def latest(self, symbol: str, *, timeout: float = 10.0):
        """Most recent live quote, or LookupError on timeout."""
        import asyncio

        async def first():
            agen = self._factory.live_ticks(symbol)
            try:
                return await asyncio.wait_for(agen.__anext__(), timeout)
            finally:
                await agen.aclose()

        try:
            return asyncio.run(first())
        except TimeoutError as error:
            raise LookupError(f"no live quotes for {symbol}") from error


class FeaturesAccessor:
    """Computed features: read the log, write new values."""

    def __init__(self, factory):
        self._factory = factory

    def of_symbol(self, symbol: str, feature: str | None = None):
        """Stored rows for one symbol, oldest first."""
        from mrmkt.command.list_features import ListFeaturesRequest

        result = self._factory.list_features().execute(
            ListFeaturesRequest(symbol=symbol)
        )
        rows = _check(result, what=f"features for {symbol}")
        if feature is not None:
            rows = [row for row in rows if row.feature == feature]
        return rows

    def latest(self, symbol: str, feature: str):
        """Latest stored value for one symbol+feature."""
        from mrmkt.command.show_feature import ShowFeatureRequest

        result = self._factory.show_feature().execute(
            ShowFeatureRequest(symbol=symbol, name=feature)
        )
        return _check(result, what=f"feature {feature} for {symbol}")

    def create(self, symbol: str, assignment: str, date: str | None = None):
        """Store one value (name=value); returns the stored row."""
        from mrmkt.command.create_feature import CreateFeatureRequest

        result = self._factory.create_feature().execute(
            CreateFeatureRequest(symbol=symbol, assignment=assignment, date=date)
        )
        return _check(result, what=f"feature {assignment} for {symbol}")


class SymbolsAccessor:
    """Cataloged symbols: ``mkt.symbols.with_tag("sp500")``."""

    def __init__(self, factory):
        self._factory = factory

    def with_tag(self, tag: str) -> list[str]:
        """Ticker symbols carrying a tag, in deterministic order."""
        checked = normalize_tag(tag)
        result = self._factory.list_symbols().execute(ListSymbolsRequest(tag=checked))
        tickers = _check(result, what=f"symbols with tag {tag}")
        return list(dict.fromkeys(t.ticker for t in tickers))


class MrMkt:
    """Scripting session; close it or use it as a context manager."""

    def __init__(self, context: AppContext):
        self._context = context
        self.features = FeaturesAccessor(context.command_factory)
        self.prices_historical = PricesAccessor(context.command_factory)
        self.prices_realtime = RealtimeAccessor(context.command_factory)
        self.symbols = SymbolsAccessor(context.command_factory)

    def close(self) -> None:
        """Release backend resources."""
        self._context.close()

    def __enter__(self) -> "MrMkt":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def connect(*, backend: str | None = None) -> MrMkt:
    """Open a scripting session with default config, like the CLI.

    Pass ``backend=`` (``"postgres"``, ``"api"``, ...) to override
    ``MRMKT_BACKEND``. Use as a context manager so resources release::

        with mrmkt.connect() as mkt:
            bars = mkt.prices_historical.of_symbol("SPY")
    """
    return MrMkt(create_app_context(backend_name=backend))
