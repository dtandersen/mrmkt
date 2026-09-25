"""Live price watcher with transition-only risk-range alerts."""

import os
from datetime import date

from mrmkt.command._shared import (
    _resolve_signal,
    load_local_config,
    normalize_symbol,
    normalize_tag,
    parse_cli_date,
)
from mrmkt.command.alerts import (
    NTFY_ENV_VAR,
    AlertEngine,
    FanoutSink,
    FileSink,
    LevelsUseCase,
    ListSink,
    NtfySink,
    StdoutSink,
    TriggerRule,
    dry_run_alerts,
    format_alert,
    resolve_ntfy_url,
)
from mrmkt.entity.trigger import Trigger


def build_alert_sink(
    name: str, file_path: str | None = None, local_config: dict | None = None
):
    """Build a named alert sink; secrets come from env/config, never the repo."""
    if name == "stdout":
        return StdoutSink()
    if name == "file":
        if not file_path:
            raise ValueError("--sink-file is required for the file sink")
        return FileSink(file_path)
    if name == "ntfy":
        url = resolve_ntfy_url(os.environ.get(NTFY_ENV_VAR, ""), local_config or {})
        if not url:
            raise ValueError(
                f"set {NTFY_ENV_VAR} or the ntfy topic in local config.yaml"
            )
        return NtfySink(url)
    raise ValueError(f"unknown sink {name!r} (choose stdout, file, ntfy)")


class WatchPrices:
    """Watch live prices and alert once per buy-level touch (deduped to re-arm).

    Streaming output goes through ``emit``; the live price stream arrives
    through ``stream_runner`` so the command itself never touches the
    network or builds gateway clients.
    """

    def __init__(self, repository, clock, stream_runner, emit):
        self.repository = repository
        self.clock = clock
        self.stream_runner = stream_runner
        self.emit = emit

    def execute(
        self,
        symbols: list[str] | None,
        tags: list[str] | None,
        signal: str,
        sinks: list[str] | None,
        sink_file: str | None,
        feed: str,
        dry_run: bool,
        session_policy: str,
        as_of: str | None,
        verbose: bool,
        trigger_ids: list[int] | None,
        all_triggers: bool,
    ) -> None:
        _resolve_signal(signal)
        use_store = bool(trigger_ids) or all_triggers
        if use_store and (symbols or tags):
            raise ValueError(
                "use either symbols/--tag or stored triggers, not both"
            )
        if not use_store and not symbols and not tags:
            raise ValueError(
                "provide symbols, --tag, --trigger-id, or --all-triggers"
            )
        if session_policy not in ("regular", "extended"):
            raise ValueError("--session-policy must be regular or extended")
        if feed not in ("iex", "sip"):
            raise ValueError("--feed must be iex or sip")
        sink_names = sinks or ["stdout"]
        local_config = load_local_config()
        try:
            fanout = FanoutSink(
                [build_alert_sink(name, sink_file, local_config) for name in sink_names]
            )
        except ValueError as error:
            raise ValueError(str(error)) from error
        today = self.clock.today()
        try:
            as_of_date = parse_cli_date(as_of, today) if as_of is not None else None
        except ValueError as error:
            raise ValueError(
                "dates must be ISO dates, now, or durations such as 180d"
            ) from error
        repository = self.repository
        stored_triggers: list[Trigger] = []
        if use_store:
            wanted_ids = set(trigger_ids or [])
            for trigger in repository.list_triggers(enabled_only=True):
                if trigger.id is None:
                    continue
                if all_triggers or trigger.id in wanted_ids:
                    stored_triggers.append(trigger)
            if all_triggers and not stored_triggers:
                self.emit("No enabled triggers in the store.")
                return
            if trigger_ids and len(stored_triggers) != len(wanted_ids):
                found = {t.id for t in stored_triggers}
                missing = sorted(wanted_ids - found)
                raise ValueError(f"no enabled trigger with id {missing}")
            seen: dict[str, Trigger] = {}
            for trigger in sorted(stored_triggers, key=lambda t: t.id or 0):
                if trigger.symbol in seen:
                    raise ValueError(
                        f"multiple triggers for {trigger.symbol}; refine --trigger-id selection"
                    )
                seen[trigger.symbol] = trigger
            selected = sorted(seen)
        else:
            selected = sorted(
                {normalize_symbol(symbol) for symbol in (symbols or [])}
                | {
                    symbol
                    for tag in (tags or [])
                    for symbol in repository.get_symbols_by_tag(normalize_tag(tag))
                }
            )
        try:
            levels = LevelsUseCase(repository).execute(
                include_tags=[], symbols=selected, as_of=as_of_date
            )
        except ValueError as error:
            # Levels validation failures surface through the generic
            # failure path like before.
            raise RuntimeError(str(error)) from error
        if not levels.rows:
            self.emit("No symbols with enough history for levels.")
            return
        trigger_by_symbol = {t.symbol: t for t in stored_triggers}
        disabled_ids: list[int] = []

        def on_fire(alert) -> None:
            fanout(alert)
            trigger = trigger_by_symbol.get(alert.symbol)
            if (
                trigger is not None
                and trigger.frequency == "once"
                and trigger.id is not None
                and not dry_run
            ):
                repository.set_trigger_enabled(trigger.id, False)
                disabled_ids.append(trigger.id)

        engine = AlertEngine(on_alert=on_fire, session_policy=session_policy)
        preset_levels: dict[str, float] = {}
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
                if trigger.value is not None:
                    preset_levels[row.symbol] = trigger.value
                    engine.set_levels({row.symbol: trigger.value})
                    engine.frozen.add(row.symbol)
                else:
                    engine.set_levels({row.symbol: row.range_low})
            else:
                engine.set_levels({row.symbol: row.range_low})
        engine.seed_baseline({row.symbol: row.close for row in levels.rows})
        if verbose:
            engine.on_ignored = lambda tick: self.emit(
                f"{tick.moment.isoformat()} | {tick.session} | {tick.symbol} | "
                f"{tick.price:g} vs buy {tick.level:g} IGNORED ({tick.reason})"
            )
        if dry_run:
            # Recording sink only: --dry-run can never deliver to real
            # sinks. Levels/arm state advance bar by bar (no lookahead).
            # Stored-trigger rules carry over; `once` triggers are not
            # disabled in dry runs (no store writes).
            recorder = ListSink()
            dry_engine = AlertEngine(on_alert=recorder, session_policy=session_policy)
            for row in levels.rows:
                trigger = trigger_by_symbol.get(row.symbol)
                if trigger is not None:
                    dry_engine.set_rule(
                        row.symbol,
                        TriggerRule(
                            operator=trigger.operator,
                            frequency=trigger.frequency,
                            expires_at=trigger.expires_at,
                            message=trigger.message,
                        ),
                    )
            bars_by_symbol: dict = {}
            for price in repository.list_prices_for_symbols(
                [row.symbol for row in levels.rows], date.min, as_of_date or today
            ):
                bars_by_symbol.setdefault(price.symbol, []).append(price)
            self.emit(
                "# dry-run: replaying stored daily lows as regular-session "
                "ticks; sinks not called"
            )
            for alert in dry_run_alerts(
                dry_engine, bars_by_symbol, preset_levels=preset_levels
            ):
                self.emit(f"would alert: {format_alert(alert)}")
            return
        self.emit(
            f"Watching {len(levels.rows)} symbols ({session_policy} sessions fire); "
            f"levels as of {levels.data_vintage}."
        )
        self.stream_runner([row.symbol for row in levels.rows], engine, feed)
