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
from urllib.parse import quote, urlsplit

import typer
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient

from mrmkt.backend import MrMktBackendFactory
from mrmkt.command import _shared
from mrmkt.command.add_triggerset import AddTriggerToSet
from mrmkt.command.backtest_run import RunBacktest
from mrmkt.command.base import Console, Log
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
from mrmkt.command.start_engine import DEFAULT_SUBJECT, StartEngine
from mrmkt.command.symbols_label import LabelSymbols
from mrmkt.command.symbols_unlabel import UnlabelSymbols
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.command.triggersets_common import _default_set_name
from mrmkt.command.watch import WatchPrices
from mrmkt.common.clock import Clock
from mrmkt.common.env import MrMktEnvironment2
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.ext.rabbitmq import RabbitMQMessageQueue
from mrmkt.ext.repo.alpaca import AlpacaTickerRepository
from mrmkt.ext.tiingo_prices import TiingoPriceSource
from mrmkt.gateway import MessageQueue, PriceProvider, PriceSource, Quote


class CommandFactory:
    """One shared factory handing ready commands to every CLI handler.

    The factory holds only the environment. Handlers take a ready command
    from a named constructor::

        command = env.command_factory.create_trigger()
        stored = command.execute(name, symbol, ...)

    The repository opener behind the environment opens once per CLI
    invocation; its release runs once at teardown.
    """

    def __init__(
        self,
        env: MrMktEnvironment2,
        watch_price_source: PriceSource | None = None,
        engine_queue: MessageQueue | None = None,
        engine_prices: PriceProvider | None = None,
        console: Console | None = None,
        log: Log | None = None,
    ) -> None:
        self._env = env
        self._watch_price_source = watch_price_source
        self._engine_queue = engine_queue
        self._engine_prices = engine_prices
        self._console = console or TyperConsole()
        self._log = log or TeeLog()

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

    def import_prices(self, provider: str = "alpaca") -> ImportPrices:
        """Build a ready ImportPrices from the app-scoped environment."""
        if provider.lower() == "tiingo":
            price_source: Any = TiingoPriceSource.from_env(self._log)
        else:
            price_source = AlpacaPriceSource(self._env.alpaca_data_client, self._log)
        return ImportPrices(
            price_source=price_source,
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
        if self._watch_price_source is not None:
            price_source = self._watch_price_source
        elif self._engine_queue is not None:
            price_source = QueuePriceSource(self._engine_queue, self._log)
        else:
            rabbitmq_url = rabbitmq_url_from_config()
            price_source = QueuePriceSource(
                RabbitMQMessageQueue(rabbitmq_url),
                self._log,
                address=rabbitmq_display_address(rabbitmq_url),
            )
        return WatchPrices(
            self._env.triggers,
            price_source,
            self._console,
            self._log,
            ranges=ListRanges(self._env.triggers, self._env.clock),
        )

    def start_engine(self) -> StartEngine:
        """Build a ready StartEngine from the app-scoped environment."""
        queue = (
            self._engine_queue
            if self._engine_queue is not None
            else RabbitMQMessageQueue(rabbitmq_url_from_config())
        )
        prices = (
            self._engine_prices
            if self._engine_prices is not None
            else TiingoFirehosePrices(self._log)
        )
        return StartEngine(self._env.triggers, queue, prices, self._console, self._log)

    async def live_ticks(self, symbol):
        """Yield live quotes; Tiingo firehose unless tests inject a fake."""
        import asyncio
        import threading

        provider = (
            self._engine_prices
            if self._engine_prices is not None
            else TiingoFirehosePrices(self._log)
        )
        queue: asyncio.Queue[Quote] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_quote(quote: Quote) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, quote)

        thread = threading.Thread(
            target=provider.subscribe,
            args=([symbol],),
            kwargs={"on_quote": on_quote},
            daemon=True,
            name=f"mrmkt-live-{symbol}",
        )
        thread.start()
        try:
            while True:
                yield await queue.get()
        finally:
            provider.close()
            thread.join(timeout=5)
            if thread.is_alive():
                self._log(f"live stream thread for {symbol} did not stop")


@dataclass(frozen=True)
class AppContext:
    """Shared, app-level CLI dependencies installed on the Typer context."""

    command_factory: CommandFactory
    close: Callable[[], None]


def _report_price_import_progress(done: int, total: int) -> None:
    typer.echo(f"Imported prices for {done}/{total} symbols...", err=True)


def rabbitmq_display_address(url: str) -> str:
    """Broker label for log lines; never includes credentials from the URL."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or "localhost"
        port = parts.port or 5672
    except ValueError:
        return "RabbitMQ"
    return f"RabbitMQ@{host}:{port}"


class TiingoFirehosePrices(PriceProvider):
    """Production PriceProvider: Tiingo equity firehose -> normalized quotes."""

    def __init__(self, log: Log):
        self.log = log
        self._stream = None

    def subscribe(
        self, symbols: list[str], *, on_quote: Callable[[Quote], None]
    ) -> None:
        import datetime

        from mrmkt.common.clock import ET
        from mrmkt.ext.tiingo_stream import TiingoFirehose

        stream = TiingoFirehose.from_env(
            lambda: datetime.datetime.now(tz=ET),
            log=self.log,
        )
        self._stream = stream
        stream.subscribe(symbols, "cons", on_quote=on_quote)

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.close()


class QueuePriceSource:
    """PriceSource over the message queue: per-symbol data subjects.

    The engine publishes each symbol's quotes under its own subject;
    attach to one subject per requested symbol. Transport details stay
    here in the composition root; the command only sees normalized
    quote callbacks.
    """

    def __init__(
        self,
        queue: MessageQueue,
        log: Log,
        subject: str = DEFAULT_SUBJECT,
        *,
        address: str | None = None,
    ):
        self.queue = queue
        self.log = log
        self.subject = subject
        self.address = address or "price queue"

    def subscribe(self, symbols: list[str], feed: str, *, on_quote) -> None:
        if not symbols:
            return
        self.log(f"Connecting to {self.address}")
        self.log(f"Subscribing to {', '.join(symbols)}")
        for symbol in symbols:
            self.queue.subscribe(f"{self.subject}.{symbol}", on_event=on_quote)


DEFAULT_LOG_PATH = "mrmkt.log"


class TyperConsole(Console):
    """User-facing output through typer."""

    def __call__(self, line: str) -> None:
        typer.echo(line)


class TeeLog(Log):
    """Operational record to stdout and a log file."""

    def __init__(self, path: str = DEFAULT_LOG_PATH):
        self.path = path

    def __call__(self, line: str) -> None:
        import sys

        print(line, flush=True)
        try:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as error:
            print(f"log file write failed: {error}", file=sys.stderr, flush=True)


def mrmkt_backend_factory_from_env(
    local_repository,
) -> MrMktBackendFactory:
    """Build the backend factory from environment configuration.

    ``MRMKT_BACKEND`` names the backend (``postgres`` by default,
    ``api`` for the cluster service); ``MRMKT_API_URL`` and
    ``MRMKT_API_TOKEN`` carry the API connection details and are never
    logged. Call ``create(name)`` on the result to build a backend.
    """
    import os

    return MrMktBackendFactory(
        local_repository=local_repository,
        api_url=os.environ.get("MRMKT_API_URL") or None,
        api_token=os.environ.get("MRMKT_API_TOKEN") or None,
    )


def mrmkt_backend_name_from_env() -> str:
    """Read the selected backend name (default ``postgres``)."""
    import os

    return os.environ.get("MRMKT_BACKEND", "postgres")


def rabbitmq_url_from_section(section: dict) -> str:
    """Build the RabbitMQ URL from a config mapping (see docker-compose)."""
    if not isinstance(section, dict):
        section = {}
    user = quote(str(section.get("user", "mrmkt")), safe="")
    password = quote(str(section.get("password", "mrmkt")), safe="")
    host = section.get("host", "localhost")
    port = section.get("port", 5672)
    return f"amqp://{user}:{password}@{host}:{port}/"


def rabbitmq_url_from_config() -> str:
    """RabbitMQ URL for the engine bus.

    Explicit ``RABBITMQ_URL`` wins (used by the docker run command);
    otherwise the ``rabbitmq`` section of config.yaml, which carries the
    same credentials as docker-compose; a missing config.yaml falls back
    to those same local dev defaults. Credentials never live in the repo.
    """
    import os

    override = os.environ.get("RABBITMQ_URL")
    if override:
        return override
    try:
        from mrmkt.common.config import read_config

        config = read_config()
    except OSError:
        config = {}
    section = config.get("rabbitmq", {}) if isinstance(config, dict) else {}
    return rabbitmq_url_from_section(section)


def _close_all(backend, release) -> None:
    """Release the backend, then the shared local resources."""
    try:
        backend.close()
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
    backend = mrmkt_backend_factory_from_env(repository).create(
        mrmkt_backend_name_from_env()
    )
    env = MrMktEnvironment2(
        financials=repository,
        prices=repository,
        tickers=repository,
        tags=repository,
        triggers=backend,
        trigger_sets=repository,
        clock=clock,
        alpaca_client=alpaca_client,
        alpaca_data_client=alpaca_data_client,
        trigger_name_generator=_default_trigger_name,
        triggerset_name_generator=_default_set_name,
    )
    factory = CommandFactory(env)
    return AppContext(
        command_factory=factory, close=lambda: _close_all(backend, release)
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
    triggers: Any | None = None,
    watch_price_source: PriceSource | None = None,
    engine_queue: MessageQueue | None = None,
    engine_prices: PriceProvider | None = None,
    console: Console | None = None,
    log: Log | None = None,
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
    )
    factory = CommandFactory(
        env,
        watch_price_source=watch_price_source,
        engine_queue=engine_queue,
        engine_prices=engine_prices,
        console=console,
        log=log,
    )
    return AppContext(command_factory=factory, close=release)
