"""Composition root for CLI dependencies (outer layer).

CLI handlers never construct repositories, clients, commands, or name
generators directly. ``cli/main.py`` installs one shared
:class:`CliDependencies` on the Typer context from a root callback (tests
may inject their own through ``CliRunner(..., obj=...)`` instead), and
every handler obtains its command through the shared
:attr:`CliDependencies.command_factory`, asking for the command by class::

    with deps.command_factory(AddTriggerToSet) as add_command:
        add_command.execute(set_name, trigger_name)

The factory opens only the collaborators a command needs and releases
them when the ``with`` block exits, on success and on error alike.
Production providers dereference the legacy ``mrmkt.command._shared``
builders lazily at call time; :func:`cli_dependencies_for_testing` lets tests
override any provider with a fake without touching anything else.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

import typer

from mrmkt.command import _shared
from mrmkt.command.add_triggerset import AddTriggerToSet
from mrmkt.command.backtest_run import RunBacktest
from mrmkt.command.create_trigger import CreateTrigger
from mrmkt.command.create_triggerset import CreateTriggerSet
from mrmkt.command.delete_trigger import DeleteTrigger
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
from mrmkt.command.prices_import import ImportPrices
from mrmkt.command.ranges import ListRanges
from mrmkt.command.remove_triggerset import RemoveTriggerFromSet
from mrmkt.command.screen import ScreenSymbols
from mrmkt.command.show_trigger import ShowTrigger
from mrmkt.command.signals_current import CurrentSignals
from mrmkt.command.symbols_import import ImportSymbols
from mrmkt.command.symbols_label import LabelSymbols
from mrmkt.command.symbols_unlabel import UnlabelSymbols
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.command.triggersets_common import _default_set_name
from mrmkt.command.watch import WatchPrices
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.ext.alpaca_prices import AlpacaPriceSource

T = TypeVar("T")

# A dependency provider opens a collaborator and returns it with its release callable.
DependencyProvider = Callable[[], tuple[Any, Callable[[], None]]]
# A repository provider is the same shape, kept explicit for readability.
RepositoryFactory = DependencyProvider


def _noop() -> None:
    """Release callable for collaborators that hold no resources."""


def _open_repository() -> tuple[Any, Callable[[], None]]:
    # Late attribute lookup: honors the legacy test seam that patches
    # ``mrmkt.command._shared`` builders until those tests move to injection.
    return _shared.create_local_ticker_repository()


def _open_clock() -> tuple[Any, Callable[[], None]]:
    return _shared.create_clock(), _noop


def _open_alpaca_client() -> tuple[Any, Callable[[], None]]:
    return _shared.create_alpaca_client(), _noop


def _open_alpaca_data_client() -> tuple[Any, Callable[[], None]]:
    return _shared.create_alpaca_data_client(), _noop


def _open_trigger_name_generator() -> tuple[Any, Callable[[], None]]:
    return _default_trigger_name, _noop


def _open_triggerset_name_generator() -> tuple[Any, Callable[[], None]]:
    return _default_set_name, _noop


_DEFAULT_PROVIDERS: dict[str, DependencyProvider] = {
    "repository": _open_repository,
    "clock": _open_clock,
    "alpaca_client": _open_alpaca_client,
    "alpaca_data_client": _open_alpaca_data_client,
    "trigger_name_generator": _open_trigger_name_generator,
    "triggerset_name_generator": _open_triggerset_name_generator,
}


class _CommandScope:
    """Collaborators opened for one command; released together afterwards."""

    def __init__(self, providers: dict[str, DependencyProvider]) -> None:
        self._providers = providers
        self._resources: dict[str, Any] = {}
        self._closers: list[Callable[[], None]] = []

    def use(self, name: str) -> Any:
        """Return the named collaborator, opening it on first use."""
        if name not in self._resources:
            resource, close = self._providers[name]()
            self._resources[name] = resource
            self._closers.append(close)
        return self._resources[name]

    def close(self) -> None:
        """Release everything opened, even if one release fails."""
        failures: list[Exception] = []
        while self._closers:
            close = self._closers.pop()
            try:
                close()
            except Exception as error:
                failures.append(error)
        if failures:
            raise failures[0]

    def __enter__(self) -> "_CommandScope":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        self.close()
        return False


class CommandFactory:
    """One shared factory handing ready commands to every CLI handler.

    Handlers ask for a command by class; unknown classes fail loudly
    instead of being wired ad hoc in the handler.
    """

    def __init__(
        self,
        providers: dict[str, DependencyProvider],
        builders: dict[type, Callable[[_CommandScope], Any]],
    ) -> None:
        self._providers = providers
        self._builders = builders

    def __call__(self, command_type: type[T]) -> AbstractContextManager[T]:
        return self._open(command_type)

    @contextmanager
    def _open(self, command_type: type[T]) -> Any:
        build = self._builders.get(command_type)
        if build is None:
            name = getattr(command_type, "__name__", command_type)
            raise LookupError(f"no command registered for {name!r}")
        scope = _CommandScope(self._providers)
        with scope:
            yield build(scope)


@dataclass(frozen=True)
class CliDependencies:
    """Shared, app-level CLI dependencies installed on the Typer context."""

    command_factory: CommandFactory


def _build_add_trigger_to_set(scope: _CommandScope) -> AddTriggerToSet:
    return AddTriggerToSet(scope.use("repository"))


def _build_create_trigger_set(scope: _CommandScope) -> CreateTriggerSet:
    return CreateTriggerSet(
        scope.use("repository"),
        name_generator=scope.use("triggerset_name_generator"),
    )


def _build_remove_trigger_from_set(scope: _CommandScope) -> RemoveTriggerFromSet:
    return RemoveTriggerFromSet(scope.use("repository"))


def _build_create_trigger(scope: _CommandScope) -> CreateTrigger:
    return CreateTrigger(
        scope.use("repository"),
        name_generator=scope.use("trigger_name_generator"),
    )


def _build_list_triggers(scope: _CommandScope) -> ListTriggers:
    return ListTriggers(scope.use("repository"))


def _build_show_trigger(scope: _CommandScope) -> ShowTrigger:
    return ShowTrigger(scope.use("repository"))


def _build_delete_trigger(scope: _CommandScope) -> DeleteTrigger:
    return DeleteTrigger(scope.use("repository"))


def _build_list_symbols(scope: _CommandScope) -> ListSymbols:
    return ListSymbols(scope.use("repository"))


def _build_label_symbols(scope: _CommandScope) -> LabelSymbols:
    return LabelSymbols(scope.use("repository"))


def _build_unlabel_symbols(scope: _CommandScope) -> UnlabelSymbols:
    return UnlabelSymbols(scope.use("repository"))


def _build_import_symbols(scope: _CommandScope) -> ImportSymbols:
    return ImportSymbols(
        remote=AlpacaTickerRepository(scope.use("alpaca_client")),
        local=scope.use("repository"),
    )


def _build_list_prices(scope: _CommandScope) -> ListPrices:
    return ListPrices(scope.use("repository"), scope.use("clock"))


def _report_price_import_progress(done: int, total: int) -> None:
    typer.echo(f"Imported prices for {done}/{total} symbols...", err=True)


def _build_import_prices(scope: _CommandScope) -> ImportPrices:
    return ImportPrices(
        price_source=AlpacaPriceSource(scope.use("alpaca_data_client")),
        local_repository=scope.use("repository"),
        clock=scope.use("clock"),
        on_progress=_report_price_import_progress,
    )


def _build_check_freshness(scope: _CommandScope) -> CheckFreshness:
    return CheckFreshness(scope.use("repository"), scope.use("clock"))


def _build_run_backtest(scope: _CommandScope) -> RunBacktest:
    return RunBacktest(scope.use("repository"), scope.use("clock"))


def _build_current_signals(scope: _CommandScope) -> CurrentSignals:
    return CurrentSignals(scope.use("repository"), scope.use("clock"))


def _build_screen_symbols(scope: _CommandScope) -> ScreenSymbols:
    return ScreenSymbols(scope.use("repository"), scope.use("clock"))


def _build_list_ranges(scope: _CommandScope) -> ListRanges:
    return ListRanges(scope.use("repository"), scope.use("clock"))


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
    AlpacaStreamSource(
        stream, engine, lambda: datetime.datetime.now(tz=ET)
    ).start(symbols)


def _build_watch_prices(scope: _CommandScope) -> WatchPrices:
    return WatchPrices(
        scope.use("repository"),
        scope.use("clock"),
        _run_live_stream,
        _emit_watch_line,
    )


def _build_indicator_series(
    command_type,
) -> Callable[[_CommandScope], Any]:
    def build(scope: _CommandScope):
        return command_type(scope.use("repository"), scope.use("clock"))

    return build


_BUILDERS: dict[type, Callable[[_CommandScope], Any]] = {
    AddTriggerToSet: _build_add_trigger_to_set,
    CreateTriggerSet: _build_create_trigger_set,
    RemoveTriggerFromSet: _build_remove_trigger_from_set,
    CreateTrigger: _build_create_trigger,
    ListTriggers: _build_list_triggers,
    ShowTrigger: _build_show_trigger,
    DeleteTrigger: _build_delete_trigger,
    ListSymbols: _build_list_symbols,
    LabelSymbols: _build_label_symbols,
    UnlabelSymbols: _build_unlabel_symbols,
    ImportSymbols: _build_import_symbols,
    ListPrices: _build_list_prices,
    ImportPrices: _build_import_prices,
    CheckFreshness: _build_check_freshness,
    CalculateSma: _build_indicator_series(CalculateSma),
    CalculateRiskRange: _build_indicator_series(CalculateRiskRange),
    CalculateVolatility: _build_indicator_series(CalculateVolatility),
    CalculateVolatilityPercentile: _build_indicator_series(
        CalculateVolatilityPercentile
    ),
    CalculateVolOfVol: _build_indicator_series(CalculateVolOfVol),
    CalculateVolOfVolPercentile: _build_indicator_series(
        CalculateVolOfVolPercentile
    ),
    RunBacktest: _build_run_backtest,
    CurrentSignals: _build_current_signals,
    ScreenSymbols: _build_screen_symbols,
    ListRanges: _build_list_ranges,
    WatchPrices: _build_watch_prices,
}


def default_cli_dependencies() -> CliDependencies:
    """Production wiring installed by the CLI root callback."""
    return CliDependencies(
        command_factory=CommandFactory(dict(_DEFAULT_PROVIDERS), _BUILDERS)
    )


def resolve_cli_dependencies(ctx: typer.Context | None) -> CliDependencies:
    """Return the shared dependencies installed on the Typer context, else defaults."""
    obj = getattr(ctx, "obj", None)
    if isinstance(obj, CliDependencies):
        return obj
    return default_cli_dependencies()


def cli_dependencies_for_testing(
    *,
    repository_factory: RepositoryFactory | None = None,
    clock: Any | None = None,
    alpaca_client: Any | None = None,
    alpaca_data_client: Any | None = None,
    trigger_name_generator: Callable[[], str] | None = None,
    triggerset_name_generator: Callable[[], str] | None = None,
) -> CliDependencies:
    """Injectable dependencies for ``CliRunner(..., obj=...)`` tests.

    Only the fakes a test cares about need stating; everything else falls
    back to the production providers.
    """
    providers = dict(_DEFAULT_PROVIDERS)
    if repository_factory is not None:
        providers["repository"] = repository_factory
    if clock is not None:
        providers["clock"] = lambda: (clock, _noop)
    if alpaca_client is not None:
        providers["alpaca_client"] = lambda: (alpaca_client, _noop)
    if alpaca_data_client is not None:
        providers["alpaca_data_client"] = lambda: (alpaca_data_client, _noop)
    if trigger_name_generator is not None:
        providers["trigger_name_generator"] = lambda: (trigger_name_generator, _noop)
    if triggerset_name_generator is not None:
        providers["triggerset_name_generator"] = lambda: (
            triggerset_name_generator,
            _noop,
        )
    return CliDependencies(command_factory=CommandFactory(providers, _BUILDERS))
