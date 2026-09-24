"""Live price watcher with transition-only risk-range alerts."""

import datetime
import os
from collections.abc import Callable
from datetime import date
from pathlib import Path

import typer
import yaml

from mrmkt.command import _shared
from mrmkt.command._shared import normalize_symbol, normalize_tag
from mrmkt.entity.trigger import Trigger
from mrmkt.usecase.alerts import (
    ET,
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


def run(
    symbols: list[str] | None = None,
    tags: list[str] | None = None,
    sinks: list[str] | None = None,
    sink_file: str | None = None,
    feed: str = "iex",
    dry_run: bool = False,
    session_policy: str = "regular",
    as_of: str | None = None,
    verbose: bool = False,
    trigger_ids: list[int] | None = None,
    all_triggers: bool = False,
) -> None:
    """Watch live prices and alert once per buy-level touch (deduped to re-arm)."""
    use_store = bool(trigger_ids) or all_triggers
    if use_store and (symbols or tags):
        raise typer.BadParameter(
            "use either symbols/--tag or stored triggers, not both"
        )
    if not use_store and not symbols and not tags:
        raise typer.BadParameter(
            "provide symbols, --tag, --trigger-id, or --all-triggers"
        )
    if session_policy not in ("regular", "extended"):
        raise typer.BadParameter("--session-policy must be regular or extended")
    if feed not in ("iex", "sip"):
        raise typer.BadParameter("--feed must be iex or sip")
    sink_names = sinks or ["stdout"]
    local_config = _shared.load_local_config()
    try:
        fanout = FanoutSink(
            [build_alert_sink(name, sink_file, local_config) for name in sink_names]
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    today = _shared.create_clock().today()
    try:
        as_of_date = _shared.parse_cli_date(as_of, today) if as_of is not None else None
    except ValueError as error:
        raise typer.BadParameter(
            "dates must be ISO dates, now, or durations such as 180d"
        ) from error
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        stored_triggers: list[Trigger] = []
        if use_store:
            wanted_ids = set(trigger_ids or [])
            for trigger in repository.list_triggers(enabled_only=True):
                if trigger.id is None:
                    continue
                if all_triggers or trigger.id in wanted_ids:
                    stored_triggers.append(trigger)
            if all_triggers and not stored_triggers:
                typer.echo("No enabled triggers in the store.")
                return
            if trigger_ids and len(stored_triggers) != len(wanted_ids):
                found = {t.id for t in stored_triggers}
                missing = sorted(wanted_ids - found)
                raise typer.BadParameter(f"no enabled trigger with id {missing}")
            seen: dict[str, Trigger] = {}
            for trigger in sorted(stored_triggers, key=lambda t: t.id or 0):
                if trigger.symbol in seen:
                    raise typer.BadParameter(
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
        levels = LevelsUseCase(repository).execute(
            include_tags=[], symbols=selected, as_of=as_of_date
        )
        if not levels.rows:
            typer.echo("No symbols with enough history for levels.")
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
            engine.on_ignored = lambda tick: typer.echo(
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
            typer.echo(
                "# dry-run: replaying stored daily lows as regular-session "
                "ticks; sinks not called"
            )
            for alert in dry_run_alerts(
                dry_engine, bars_by_symbol, preset_levels=preset_levels
            ):
                typer.echo(f"would alert: {format_alert(alert)}")
            return
        config = yaml.safe_load(Path("alpaca.yaml").read_text())
        from alpaca.data.enums import DataFeed
        from alpaca.data.live import StockDataStream

        from mrmkt.ext.alpaca_stream import AlpacaStreamSource

        stream = StockDataStream(
            api_key=config["key"],
            secret_key=config["secret"],
            feed=DataFeed(feed),
        )
        typer.echo(
            f"Watching {len(levels.rows)} symbols ({session_policy} sessions fire); "
            f"levels as of {levels.data_vintage}."
        )
        AlpacaStreamSource(stream, engine, lambda: datetime.datetime.now(tz=ET)).start(
            [row.symbol for row in levels.rows]
        )
    except (typer.BadParameter, typer.Exit):
        raise
    except Exception as error:
        typer.echo(f"Failed to watch alerts: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
