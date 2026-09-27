"""Watch live quote asks and print signals from stored or explicit symbols."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.alerts import Alert, AlertEngine, TriggerRule
from mrmkt.command.base import BaseResult, Command, Console, Log
from mrmkt.command.ranges import ListRanges, ListRangesRequest
from mrmkt.entity.trigger import Trigger


@dataclass(frozen=True)
class Quote:
    """Normalized level-one quote from the selected price feed."""

    symbol: str
    bid: float
    ask: float
    timestamp: datetime


class PriceSource(Protocol):
    """Live source that subscribes to symbols and emits normalized quotes."""

    def subscribe(
        self,
        symbols: list[str],
        feed: str,
        *,
        on_quote: Callable[[Quote], None],
    ) -> None:
        """Subscribe and call the handler as quotes arrive."""


@dataclass(frozen=True)
class WatchPricesRequest:
    symbols: list[str] | None = None
    feed: str = "iex"
    trigger_ids: list[int] | None = None
    all_triggers: bool = False


@dataclass
class WatchPricesResult(BaseResult[None]):
    pass


class WatchPrices(Command[WatchPricesRequest, WatchPricesResult]):
    """Coordinate live quotes -> trigger analysis -> console output."""

    def __init__(
        self,
        repository,
        price_source: PriceSource,
        console: Console,
        log: Log,
        *,
        ranges: ListRanges,
    ):
        self.repository = repository
        self.price_source = price_source
        self.console = console
        self.log = log
        self.load_levels = ranges.execute

    def execute(self, request: WatchPricesRequest) -> WatchPricesResult:
        if not request.symbols and not request.trigger_ids and not request.all_triggers:
            # Bare `mrmkt watch` streams every enabled stored trigger.
            request = replace(request, all_triggers=True)
        use_store = bool(request.trigger_ids) or request.all_triggers
        if use_store and request.symbols:
            return WatchPricesResult.invalid_data(
                ["use either symbols or stored triggers, not both"]
            )
        if request.feed not in ("iex", "sip"):
            return WatchPricesResult.invalid_data(["--feed must be iex or sip"])
        try:
            self._watch(request)
        except KeyboardInterrupt:
            # Ctrl+C is the watcher's stop button: a clean stop, not a failure.
            self.console("Stopped watching.")
        except ValueError as error:
            return WatchPricesResult.invalid_data([str(error)])
        except Exception as error:
            self.log(f"Failed to watch alerts: {error}")
            return WatchPricesResult.error([f"Failed to watch alerts: {error}"])
        return WatchPricesResult.success(None)

    def _watch(self, request: WatchPricesRequest) -> None:
        triggers, symbols = self._resolve_symbols(request)
        if not symbols:
            if request.all_triggers and not triggers:
                self.console("No enabled triggers in the store.")
            else:
                self.console("No symbols with enough history for levels.")
            return

        levels_result = self.load_levels(ListRangesRequest(symbols=symbols))
        if not levels_result.is_success() or levels_result.result is None:
            raise RuntimeError("; ".join(levels_result.errors) or "levels failed")
        levels = levels_result.result
        if not levels.rows:
            self.console("No symbols with enough history for levels.")
            return

        trigger_by_symbol = {trigger.symbol: trigger for trigger in triggers}
        self._stream(request, levels, trigger_by_symbol)

    def _resolve_symbols(
        self, request: WatchPricesRequest
    ) -> tuple[list[Trigger], list[str]]:
        """Resolve selected triggers or the explicit-symbol set."""
        if request.trigger_ids or request.all_triggers:
            wanted_ids = set(request.trigger_ids or [])
            triggers = [
                trigger
                for trigger in self.repository.list_triggers(enabled_only=True)
                if trigger.id is not None
                and (request.all_triggers or trigger.id in wanted_ids)
            ]
            if request.trigger_ids and len(triggers) != len(wanted_ids):
                found = {trigger.id for trigger in triggers}
                missing = sorted(wanted_ids - found)
                raise ValueError(f"no enabled trigger with id {missing}")

            by_symbol: dict[str, Trigger] = {}
            for trigger in sorted(triggers, key=lambda item: item.id or 0):
                if trigger.symbol in by_symbol:
                    raise ValueError(
                        f"multiple triggers for {trigger.symbol}; refine --trigger selection"
                    )
                by_symbol[trigger.symbol] = trigger
            return triggers, sorted(by_symbol)

        symbols = sorted(
            {normalize_symbol(symbol) for symbol in (request.symbols or [])}
        )
        return [], symbols

    def _stream(self, request: WatchPricesRequest, levels, trigger_by_symbol) -> None:
        """Configure the analyzer, subscribe the source, and print each hit."""
        latest_bid: dict[str, float] = {}

        def consume_signal(alert: Alert) -> None:
            trigger = trigger_by_symbol.get(alert.symbol)
            name = trigger.name if trigger is not None else alert.symbol
            bid = latest_bid.get(alert.symbol, alert.price)
            self.console(f"Trigger fired: {name}")
            self.console(f"symbol: {alert.symbol}, bid: {bid:g}, ask: {alert.price:g}")
            if (
                trigger is not None
                and trigger.frequency == "once"
                and trigger.id is not None
            ):
                self.repository.set_trigger_enabled(trigger.id, False)

        engine = AlertEngine(on_alert=consume_signal)
        for row in levels.rows:
            trigger = trigger_by_symbol.get(row.symbol)
            if trigger is not None:
                engine.set_rule(
                    row.symbol,
                    TriggerRule(
                        operator=trigger.operator,
                        frequency=trigger.frequency,
                        expires_at=trigger.expires_at,
                        message=trigger.message,
                    ),
                )
            if trigger is not None and trigger.value is not None:
                engine.set_levels({row.symbol: trigger.value})
                engine.frozen.add(row.symbol)
            else:
                engine.set_levels({row.symbol: row.range_low})
        engine.seed_baseline({row.symbol: row.close for row in levels.rows})

        symbols = [row.symbol for row in levels.rows]
        self.console(
            f"Watching {len(levels.rows)} symbols (regular sessions fire); "
            f"levels as of {levels.data_vintage}."
        )

        def handle_quote(quote: Quote) -> None:
            # For a long entry, the ask is the displayed price to buy at.
            latest_bid[quote.symbol] = quote.bid
            engine.on_tick(quote.symbol, quote.ask, quote.timestamp)

        self.price_source.subscribe(
            symbols,
            request.feed,
            on_quote=handle_quote,
        )
