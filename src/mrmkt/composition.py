"""Composition root for CLI dependencies (outer layer).

CLI handlers never construct repositories, clients, commands, or name
generators directly. ``cli/main.py`` installs one shared
:class:`CliDependencies` on the Typer context from a root callback (tests
may inject their own through ``CliRunner(..., obj=...)`` instead), and
every handler obtains its command from a named constructor on the shared
:attr:`CliDependencies.command_factory`::

    command = env.command_factory.create_trigger()
    stored = command.execute(name, symbol, ...)

Collaborators are app-scoped: the repository opener behind the
environment opens once per CLI invocation and its release runs once at
teardown (registered on the Typer context by ``cli/main.py``), on success
and on error alike.
Production providers dereference the legacy ``mrmkt.command._shared``
builders lazily at call time; :func:`cli_dependencies_for_testing` lets tests
override any provider with a fake without touching anything else.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import typer
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient

from mrmkt.command import _shared
from mrmkt.command.add_triggerset import AddTriggerToSet
from mrmkt.command.backtest_run import RunBacktest
from mrmkt.command.create_trigger import CreateTrigger
from mrmkt.command.create_triggerset import CreateTriggerSet
from mrmkt.command.delete_trigger import DeleteTrigger
from mrmkt.command.import_prices import ImportPrices
from mrmkt.command.import_symbols import ImportSymbols
from mrmkt.command.indicators_risk_range import CalculateRiskRange
from mrmkt.command.indicators_sma import CalculateSma
from mrmkt.command.indicators_vol_of_vol import CalculateVolOfVol
from mrmkt.command.indicators_vol_of_vol_percentile import (
    CalculateVolOfVolPercentile,
)
from mrmkt.command.indicators_volatility import CalculateVolatility
from mrmkt.command.indicators_volatility_percentile import (
    CalculateVolatilityPercentile,
)
from mrmkt.command.list_prices import ListPrices
from mrmkt.command.list_symbols import ListSymbols
from mrmkt.command.list_trigger import ListTriggers
from mrmkt.command.prices_freshness import CheckFreshness
from mrmkt.command.ranges import ListRanges
from mrmkt.command.remove_triggerset import RemoveTriggerFromSet
from mrmkt.command.screen import ScreenSymbols
from mrmkt.command.set_trigger_enabled import SetTriggerEnabled
from mrmkt.command.show_trigger import ShowTrigger
from mrmkt.command.signals_current import CurrentSignals
from mrmkt.command.symbols_label import LabelSymbols
from mrmkt.command.symbols_unlabel import UnlabelSymbols
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.command.triggersets_common import _default_set_name
from mrmkt.command.watch import WatchPrices
from mrmkt.common.clock import Clock
from mrmkt.common.env import MrMktEnvironment2
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.provider import TriggerProviderFactory


class CommandFactory:
    """One shared factory handing ready commands to every CLI handler.

    The factory holds only the environment. Handlers take a ready command
    from a named constructor::

        command = env.command_factory.create_trigger()
        stored = command.execute(name, symbol, ...)

    The repository opener behind the environment opens once per CLI
    invocation; its release runs once at teardown.
    """

    def __init__(self, env: MrMktEnvironment2) -> None:
        self._env = env

    def create_trigger(self) -> CreateTrigger:
        """Build a ready CreateTrigger from the app-scoped environment."""
        return CreateTrigger(
            self._env.triggers, name_generator=self._env.trigger_name_generator
        )

    def list_triggers(self) -> ListTriggers:
        """Build a ready ListTriggers from the app-scoped environment."""
        return ListTriggers(self._env.triggers)

    def show_trigger(self) -> ShowTrigger:
        """Build a ready ShowTrigger from the app-scoped environment."""
        return ShowTrigger(self._env.triggers)

    def delete_trigger(self) -> DeleteTrigger:
        """Build a ready DeleteTrigger from the app-scoped environment."""
        return DeleteTrigger(self._env.triggers)

    def set_trigger_enabled(self) -> SetTriggerEnabled:
        """Build a ready SetTriggerEnabled from the app-scoped environment."""
        return SetTriggerEnabled(self._env.triggers)

    def create_trigger_set(self) -> CreateTriggerSet:
        """Build a ready CreateTriggerSet from the app-scoped environment."""
        return CreateTriggerSet(
            self._env.trigger_sets,
            name_generator=self._env.triggerset_name_generator,
        )

    def add_trigger_to_set(self) -> AddTriggerToSet:
        """Build a ready AddTriggerToSet from the app-scoped environment."""
        return AddTriggerToSet(self._env.trigger_sets)

    def remove_trigger_from_set(self) -> RemoveTriggerFromSet:
        """Build a ready RemoveTriggerFromSet from the app-scoped environment."""
        return RemoveTriggerFromSet(self._env.trigger_sets)

    def import_symbols(self) -> ImportSymbols:
        """Build a ready ImportSymbols from the app-scoped environment."""
        return ImportSymbols(
            remote=AlpacaTickerRepository(self._env.alpaca_client),
            local=self._env.tickers,
        )

    def list_symbols(self) -> ListSymbols:
        """Build a ready ListSymbols from the app-scoped environment."""
        return ListSymbols(self._env.tickers)

    def label_symbols(self) -> LabelSymbols:
        """Build a ready LabelSymbols from the app-scoped environment."""
        return LabelSymbols(self._env.tickers)

    def unlabel_symbols(self) -> UnlabelSymbols:
        """Build a ready UnlabelSymbols from the app-scoped environment."""
        return UnlabelSymbols(self._env.tickers)

    def import_prices(self) -> ImportPrices:
        """Build a ready ImportPrices from the app-scoped environment."""
        return ImportPrices(
            price_source=AlpacaPriceSource(self._env.alpaca_data_client),
            local_repository=self._env.prices,
            clock=self._env.clock,
            on_progress=_report_price_import_progress,
        )

    def list_prices(self) -> ListPrices:
        """Build a ready ListPrices from the app-scoped environment."""
        return ListPrices(self._env.prices, self._env.clock)

    def check_freshness(self) -> CheckFreshness:
        """Build a ready CheckFreshness from the app-scoped environment."""
        return CheckFreshness(self._env.prices, self._env.clock)

    def calculate_sma(self) -> CalculateSma:
        """Build a ready CalculateSma from the app-scoped environment."""
        return CalculateSma(self._env.prices, self._env.clock)

    def calculate_risk_range(self) -> CalculateRiskRange:
        """Build a ready CalculateRiskRange from the app-scoped environment."""
        return CalculateRiskRange(self._env.prices, self._env.clock)

    def calculate_volatility(self) -> CalculateVolatility:
        """Build a ready CalculateVolatility from the app-scoped environment."""
        return CalculateVolatility(self._env.prices, self._env.clock)

    def calculate_volatility_percentile(self) -> CalculateVolatilityPercentile:
        """Build a ready CalculateVolatilityPercentile."""
        return CalculateVolatilityPercentile(self._env.prices, self._env.clock)

    def calculate_vol_of_vol(self) -> CalculateVolOfVol:
        """Build a ready CalculateVolOfVol from the app-scoped environment."""
        return CalculateVolOfVol(self._env.prices, self._env.clock)

    def calculate_vol_of_vol_percentile(self) -> CalculateVolOfVolPercentile:
        """Build a ready CalculateVolOfVolPercentile."""
        return CalculateVolOfVolPercentile(self._env.prices, self._env.clock)

    def run_backtest(self) -> RunBacktest:
        """Build a ready RunBacktest from the app-scoped environment."""
        return RunBacktest(self._env.prices, self._env.clock)

    def current_signals(self) -> CurrentSignals:
        """Build a ready CurrentSignals from the app-scoped environment."""
        return CurrentSignals(self._env.prices, self._env.clock)

    def screen_symbols(self) -> ScreenSymbols:
        """Build a ready ScreenSymbols from the app-scoped environment."""
        return ScreenSymbols(self._env.prices, self._env.clock)

    def list_ranges(self) -> ListRanges:
        """Build a ready ListRanges from the app-scoped environment."""
        return ListRanges(self._env.prices, self._env.clock)

    def watch_prices(self) -> WatchPrices:
        """Build a ready WatchPrices from the app-scoped environment."""
        return WatchPrices(
            self._env.triggers, self._env.clock, _run_live_stream, _emit_watch_line
        )

    async def live_ticks(self, symbol):
        """Yield live trade ticks; real Alpaca stream unless tests inject a fake."""
        from mrmkt.ext.alpaca_ticks import AlpacaTickSource

        source = (
            self._env.tick_source
            if self._env.tick_source is not None
            else AlpacaTickSource.from_config()
        )
        async for tick in source.subscribe(symbol):
            yield tick


@dataclass(frozen=True)
class AppContext:
    """Shared, app-level CLI dependencies installed on the Typer context."""

    command_factory: CommandFactory
    close: Callable[[], None]


def _report_price_import_progress(done: int, total: int) -> None:
    typer.echo(f"Imported prices for {done}/{total} symbols...", err=True)


def _emit_watch_line(line: str, err: bool = False) -> None:
    typer.echo(line, err=err)


def _run_live_stream(symbols: list[str], engine, feed: str) -> None:
    import datetime
    from pathlib import Path

    import yaml
    from alpaca.data.enums import DataFeed
    from alpaca.data.live import StockDataStream

    from mrmkt.common.clock import ET
    from mrmkt.ext.alpaca_stream import AlpacaStreamSource

    config = yaml.safe_load(Path("alpaca.yaml").read_text())
    stream = StockDataStream(
        api_key=config["key"],
        secret_key=config["secret"],
        feed=DataFeed(feed),
    )
    AlpacaStreamSource(stream, engine, lambda: datetime.datetime.now(tz=ET)).start(
        symbols
    )


def trigger_provider_factory_from_env(
    local_repository,
) -> TriggerProviderFactory:
    """Build the trigger provider factory from environment configuration.

    ``MRMKT_TRIGGER_PROVIDER`` names the backend (``postgres`` by
    default, ``api`` for the cluster service); ``MRMKT_API_URL`` and
    ``MRMKT_API_TOKEN`` carry the API connection details and are never
    logged. Call ``create(name)`` on the result to build a provider.
    """
    import os

    return TriggerProviderFactory(
        local_repository=local_repository,
        api_url=os.environ.get("MRMKT_API_URL") or None,
        api_token=os.environ.get("MRMKT_API_TOKEN") or None,
    )


def trigger_provider_name_from_env() -> str:
    """Read the selected trigger backend name (default ``postgres``)."""
    import os

    return os.environ.get("MRMKT_TRIGGER_PROVIDER", "postgres")


def _close_all(trigger_provider, release) -> None:
    """Release the trigger backend, then the shared local resources."""
    try:
        trigger_provider.close()
    finally:
        release()


def create_app_context() -> AppContext:
    """Production wiring installed by the CLI root callback.

    The repository opens lazily on first use and its release runs once at
    teardown (:attr:`CliDependencies.close`, registered on the Typer context).
    """
    repository, release = _shared.create_local_ticker_repository()
    clock = _shared.create_clock()
    alpaca_client = _shared.create_alpaca_client()
    alpaca_data_client = _shared.create_alpaca_data_client()
    trigger_provider = trigger_provider_factory_from_env(repository).create(
        trigger_provider_name_from_env()
    )
    env = MrMktEnvironment2(
        financials=repository,
        prices=repository,
        tickers=repository,
        tags=repository,
        triggers=trigger_provider.triggers(),
        trigger_sets=repository,
        clock=clock,
        alpaca_client=alpaca_client,
        alpaca_data_client=alpaca_data_client,
        trigger_name_generator=_default_trigger_name,
        triggerset_name_generator=_default_set_name,
    )
    factory = CommandFactory(env)
    return AppContext(
        command_factory=factory, close=lambda: _close_all(trigger_provider, release)
    )


def resolve_cli_dependencies(ctx: typer.Context | None) -> AppContext:
    """Return the shared dependencies installed on the Typer context, else defaults."""
    obj = getattr(ctx, "obj", None)
    if isinstance(obj, AppContext):
        return obj
    return create_app_context()


def cli_dependencies_for_testing(
    *,
    repository: Any,
    repository_release: Callable[[], None] | None = None,
    clock: Clock | None = None,
    alpaca_client: TradingClient | None = None,
    alpaca_data_client: StockHistoricalDataClient | None = None,
    trigger_name_generator: Callable[[], str] | None = None,
    triggerset_name_generator: Callable[[], str] | None = None,
    tick_source=None,
    triggers: Any | None = None,
) -> AppContext:
    """Injectable dependencies for ``CliRunner(..., obj=...)`` tests.

    Tests pass the repository fixture directly; an optional release callback
    lets resource-lifecycle scenarios verify app teardown without wrapping
    the repository in a factory.
    """
    release = repository_release if repository_release is not None else lambda: None
    env = MrMktEnvironment2(
        financials=repository,
        prices=repository,
        tickers=repository,
        tags=repository,
        triggers=(triggers if triggers is not None else repository),
        trigger_sets=repository,
        clock=clock if clock is not None else _shared.create_clock(),
        alpaca_client=alpaca_client
        if alpaca_client is not None
        else _shared.create_alpaca_client(),
        alpaca_data_client=alpaca_data_client
        if alpaca_data_client is not None
        else _shared.create_alpaca_data_client(),
        trigger_name_generator=trigger_name_generator or _default_trigger_name,
        triggerset_name_generator=triggerset_name_generator or _default_set_name,
        tick_source=tick_source,
    )
    factory = CommandFactory(env)
    return AppContext(command_factory=factory, close=release)
