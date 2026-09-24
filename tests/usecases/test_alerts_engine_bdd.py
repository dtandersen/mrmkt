"""BDD coverage for AlertEngine and dry-run replay, driven directly (no CLI)."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.usecase.alerts import AlertEngine, ListSink, TriggerRule, dry_run_alerts

FEATURE = Path(__file__).parent.parent / "features" / "command" / "alerts_engine.feature"
scenarios(str(FEATURE))

ET = ZoneInfo("America/New_York")
SESSION_HOURS = {"regular": (10, 0), "pre": (8, 0), "post": (17, 0)}


@pytest.fixture
def engine_context():
    return SimpleNamespace(
        engine=None, alerts=None, bars=None, fired=[], delivered=[],
        day=date(2026, 9, 22),
    )


def _moment(context, session):
    hour, minute = SESSION_HOURS[session]
    from datetime import datetime

    return datetime(
        context.day.year, context.day.month, context.day.day,
        hour, minute, tzinfo=ET,
    )


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} seeded above'))
def engine_seeded_above(engine_context, symbol, level):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.seed_baseline({symbol: level + 5.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} seeded above expiring yesterday'))
def engine_expiring(engine_context, symbol, level):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.set_rule(
        symbol, TriggerRule(expires_at=engine_context.day - timedelta(days=1))
    )
    engine.seed_baseline({symbol: level + 5.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} seeded above with frequency {frequency}'))
def engine_seeded_above_frequency(engine_context, symbol, level, frequency):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.set_rule(symbol, TriggerRule(frequency=frequency))
    engine.seed_baseline({symbol: level + 5.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} seeded above with message "{message}"'))
def engine_seeded_above_message(engine_context, symbol, level, message):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.set_rule(symbol, TriggerRule(message=message))
    engine.seed_baseline({symbol: level + 5.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} from below with operator {operator} and frequency {frequency}'))
def engine_from_below_frequency(engine_context, symbol, level, operator, frequency):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.set_rule(symbol, TriggerRule(operator=operator, frequency=frequency))
    engine.seed_baseline({symbol: level - 5.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@then("the fired alert text is \"AAA ping\"")
def fired_text(engine_context):
    assert engine_context.fired[-1].text == "AAA ping"


@then("the fired alert line holds TRIGGER")
def fired_default_line(engine_context):
    from mrmkt.usecase.alerts import format_alert

    assert "TRIGGER" in format_alert(engine_context.fired[-1])


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} from below with operator {operator}'))
def engine_from_below(engine_context, symbol, level, operator):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.set_rule(symbol, TriggerRule(operator=operator))
    engine.seed_baseline({symbol: level - 5.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@given(parsers.parse('stored bars for "{symbol}" with a late dip below its range'))
def stored_bars_with_dip(engine_context, symbol):
    from mrmkt.indicator.risk_range import risk_range_series

    closes = [100.0 * (1.002**i) for i in range(34)]
    level = risk_range_series(closes[:30], 15, 21, 0.5, 5)[-1].low
    days = []
    current = date(2022, 1, 3)
    while len(days) < 35:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    bars = []
    for pos, day in enumerate(days[:34]):
        close = closes[pos]
        bars.append(
            SimpleNamespace(
                symbol=symbol, date=day, open=close, high=close * 1.005,
                low=close * 0.995, close=close, volume=1000.0,
            )
        )
    dip_close = level + 1.0
    bars.append(
        SimpleNamespace(
            symbol=symbol, date=days[34], open=dip_close, high=dip_close,
            low=level - 0.5, close=dip_close, volume=1000.0,
        )
    )
    engine_context.bars = {symbol: bars}


@when(parsers.parse('"{symbol}" prints {price:f} in the {session} session'))
def print_tick(engine_context, symbol, price, session):
    fired = engine_context.engine.on_tick(symbol, price, _moment(engine_context, session))
    if fired is not None:
        engine_context.fired.append(fired)


@when(parsers.parse('"{symbol}" prints {price:f} at {stamp} UTC'))
def print_tick_utc(engine_context, symbol, price, stamp):
    from datetime import datetime

    moment = datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC"))
    fired = engine_context.engine.on_tick(symbol, price, moment)
    if fired is not None:
        engine_context.fired.append(fired)


@given(parsers.parse('an engine watching "{symbol}" at level {level:f} seeded below'))
def engine_seeded_below(engine_context, symbol, level):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({symbol: level})
    engine.seed_baseline({symbol: level - 1.0})
    engine_context.engine = engine
    engine_context.alerts = alerts


@when(parsers.parse('I build an engine with session policy "{policy}"'))
def build_bad_policy(engine_context, policy):
    try:
        AlertEngine(on_alert=ListSink(), session_policy=policy)
        engine_context.error = None
    except ValueError as error:
        engine_context.error = str(error)


@then("engine construction fails")
def construction_fails(engine_context):
    assert engine_context.error is not None


@given(parsers.parse('an engine with 40 closes of history for "{symbol}" at {price:f}'))
def engine_with_history(engine_context, symbol, price):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_history(symbol, [price * (1.001**i) for i in range(40)], date(2026, 9, 21))
    engine_context.engine = engine
    engine_context.alerts = alerts
    engine_context.symbol = symbol


@given(parsers.parse('the trigger level is {level:f} seeded from {prior:f}'))
def seed_explicit_level(engine_context, level, prior):
    engine_context.engine.set_levels({engine_context.symbol: level})
    engine_context.engine.seed_baseline({engine_context.symbol: prior})


@when(parsers.parse('a new daily bar closes at {close:f}'))
def roll_new_bar(engine_context, close):
    engine = engine_context.engine
    assert engine.roll_daily_bar(engine_context.symbol, 95.0, date(2026, 9, 21)) is None
    engine_context.new_level = engine.roll_daily_bar(
        engine_context.symbol, close, date(2026, 9, 22)
    )


@then("the buy level changes")
def level_changes(engine_context):
    assert engine_context.new_level is not None


@when("a tick between the old and new level still fires on the cross")
def tick_between_levels(engine_context):
    engine = engine_context.engine
    symbol = engine_context.symbol
    engine.on_tick(symbol, engine_context.new_level + 1.0, _moment(engine_context, "regular"))
    fired = engine.on_tick(symbol, engine_context.new_level - 0.5, _moment(engine_context, "regular"))
    assert fired is not None


@then("the symbol is armed")
def symbol_armed(engine_context):
    assert engine_context.engine.armed[engine_context.symbol] is True


@when("a trade prints 99.0 stamped pre-market but received mid-session")
def trade_stamped_pre(engine_context):
    from types import SimpleNamespace

    from mrmkt.ext.alpaca_stream import AlpacaStreamSource

    received = []

    class StubStream:
        def subscribe_trades(self, handler, *symbols):
            self.trade_handler = handler

        def subscribe_daily_bars(self, handler, *symbols):
            pass

        def run(self):
            pass

    stream = StubStream()
    AlpacaStreamSource(stream, engine_context.engine, lambda: _moment(engine_context, "regular")).start(["AAA"])
    stream.trade_handler(SimpleNamespace(symbol="AAA", price=99.0, timestamp=_moment(engine_context, "pre")))
    received.append(True)


@when("a trade prints 99.0 with no timestamp at mid-session receipt")
def trade_no_timestamp(engine_context):
    from types import SimpleNamespace

    from mrmkt.ext.alpaca_stream import AlpacaStreamSource

    class StubStream:
        def subscribe_trades(self, handler, *symbols):
            self.trade_handler = handler

        def subscribe_daily_bars(self, handler, *symbols):
            pass

        def run(self):
            pass

    stream = StubStream()
    AlpacaStreamSource(stream, engine_context.engine, lambda: _moment(engine_context, "regular")).start(["AAA"])
    stream.trade_handler(SimpleNamespace(symbol="AAA", price=99.0, timestamp=None))


@when(parsers.parse('"{symbol}" prints {price:f} in the regular session into a temp file'))
def print_to_file(engine_context, symbol, price):
    import tempfile

    from mrmkt.usecase.alerts import FanoutSink, FileSink

    with tempfile.NamedTemporaryFile("r", suffix=".log", delete=False) as tmp:
        engine_context.tmpfile = tmp.name
    engine_context.engine.on_alert = FanoutSink([engine_context.alerts, FileSink(tmp.name)])
    print_tick(engine_context, symbol, price, "regular")


@then(parsers.parse('the temp file holds a TRIGGER line for "{symbol}"'))
def file_holds_trigger(engine_context, symbol):
    with open(engine_context.tmpfile) as handle:
        content = handle.read()
    assert "TRIGGER" in content
    assert symbol in content


@when(parsers.parse('"{symbol}" prints {price:f} in the regular session to ntfy'))
def print_to_ntfy(engine_context, symbol, price):
    from unittest import mock

    from mrmkt.usecase.alerts import NtfySink

    engine_context.ntfy_calls = {}

    class Resp:
        def raise_for_status(self):
            pass

    def fake_post(url, data=None, headers=None, timeout=None):
        engine_context.ntfy_calls.update(url=url, data=data, headers=headers)
        return Resp()

    engine_context.engine.on_alert = NtfySink("https://ntfy.example/topic")
    with mock.patch("mrmkt.usecase.alerts.requests.post", side_effect=fake_post):
        print_tick(engine_context, symbol, price, "regular")


@then(parsers.parse('ntfy receives a POST with title "{title}" and priority "{priority}"'))
def ntfy_post(engine_context, title, priority):
    calls = engine_context.ntfy_calls
    assert calls["url"] == "https://ntfy.example/topic"
    assert calls["headers"]["Title"] == title
    assert calls["headers"]["Priority"] == priority
    assert "TRIGGER" in calls["data"].decode("utf-8")


@when(parsers.parse('"{symbol}" prints {price:f} in the regular session to a failing ntfy'))
def print_to_failing_ntfy(engine_context, symbol, price):
    import io
    from contextlib import redirect_stderr
    from unittest import mock

    import requests

    from mrmkt.usecase.alerts import NtfySink

    engine_context.engine.on_alert = NtfySink("https://ntfy.example/secret-topic-xyz")
    stderr = io.StringIO()

    def boom(*args, **kwargs):
        raise requests.RequestException("POST https://ntfy.example/secret-topic-xyz failed")

    with (
        mock.patch("mrmkt.usecase.alerts.requests.post", side_effect=boom),
        redirect_stderr(stderr),
    ):
        print_tick(engine_context, symbol, price, "regular")
    engine_context.stderr = stderr.getvalue()


@then("0 alerts are lost and stderr hides the topic")
def ntfy_failure_clean(engine_context):
    assert len(engine_context.fired) == 1
    assert "secret-topic-xyz" not in engine_context.stderr


@when("I resolve the ntfy URL from env and config variants")
def resolve_variants(engine_context):
    from mrmkt.usecase.alerts import resolve_ntfy_url

    engine_context.resolved = {
        "env": resolve_ntfy_url("https://env.example/t", {"ntfy": "https://cfg.example/t"}),
        "ntfy": resolve_ntfy_url("", {"ntfy": "https://cfg.example/t"}),
        "nfty": resolve_ntfy_url("", {"nfty": "https://cfg.example/t"}),
        "bare": resolve_ntfy_url("", {"ntfy": "my-topic"}),
        "empty": resolve_ntfy_url("", {}),
    }


@then("env wins over config and both ntfy spellings resolve")
def resolution_order(engine_context):
    resolved = engine_context.resolved
    assert resolved["env"] == "https://env.example/t"
    assert resolved["ntfy"] == "https://cfg.example/t"
    assert resolved["nfty"] == "https://cfg.example/t"
    assert resolved["bare"] == "https://ntfy.sh/my-topic"
    assert resolved["empty"] == ""


@when("I compute levels twice")
def compute_levels_twice(engine_context):
    from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
    from mrmkt.entity.stock_price import StockPrice
    from mrmkt.entity.ticker import Ticker
    from mrmkt.usecase.alerts import LevelsUseCase, render_levels_csv

    repo = InMemoryFinancialRepository()
    repo.add_ticker(Ticker(ticker="AAA", exchange="NASDAQ", type="us_equity"))
    price = 100.0
    day = date(2024, 1, 1)
    for _ in range(40):
        while day.weekday() >= 5:
            day += timedelta(days=1)
        repo.add_price(
            StockPrice(
                symbol="AAA", date=day, open=price, high=price * 1.005,
                low=price * 0.995, close=price, volume=1000.0,
            )
        )
        price *= 1.002
        day += timedelta(days=1)
    repo.add_tag("AAA", "NASDAQ", "universe")
    use_case = LevelsUseCase(repo)
    first = use_case.execute(include_tags=["universe"], symbols=[])
    engine_context.levels_csvs = [
        render_levels_csv(first),
        render_levels_csv(use_case.execute(include_tags=["universe"], symbols=[])),
    ]
    engine_context.level_row = first.rows[0]


@then("both levels CSVs are identical")
def levels_deterministic(engine_context):
    assert engine_context.levels_csvs[0] == engine_context.levels_csvs[1]


@then("the range low sits below the close")
def low_below_close(engine_context):
    assert engine_context.level_row.range_low < engine_context.level_row.close


@when("I dry-run the replay")
def dry_run(engine_context):
    delivered: list = []
    engine = AlertEngine(on_alert=delivered.append)
    engine_context.delivered = delivered
    engine_context.fired = dry_run_alerts(engine, engine_context.bars)


@then(parsers.parse("{count:d} alert fires"))
def count_fires(engine_context, count):
    assert len(engine_context.alerts.alerts) == count


@then(parsers.parse("{count:d} alerts fire"))
def count_fires_plural(engine_context, count):
    assert len(engine_context.alerts.alerts) == count


@then(parsers.parse("{count:d} alert fires"))
def count_fires_singular(engine_context, count):
    assert len(engine_context.alerts.alerts) == count


@then(parsers.parse("{count:d} alerts have fired in total"))
def count_total(engine_context, count):
    assert len(engine_context.alerts.alerts) == count


@then(parsers.parse("{count:d} tick is recorded ignored in the {session} session"))
def ignored_recorded(engine_context, count, session):
    ignored = engine_context.engine.ignored
    assert len(ignored) == count
    assert ignored[0].session == session


@then(parsers.parse("{count:d} tick is recorded ignored as expired"))
def ignored_expired(engine_context, count):
    ignored = engine_context.engine.ignored
    assert len(ignored) == count
    assert ignored[0].reason == "trigger expired"


@then("every fired alert has price at or below its level")
def alerts_below_level(engine_context):
    assert engine_context.fired, "expected the dip to trigger"
    for alert in engine_context.fired:
        assert alert.price <= alert.level


@then("delivery happened only through on_alert")
def only_on_alert(engine_context):
    assert engine_context.delivered == engine_context.fired
