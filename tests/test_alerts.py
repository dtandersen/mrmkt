"""Unit tests for risk-range alerts: sessions, engine, sinks, stream."""

import unittest
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import requests_mock
from hamcrest import assert_that, equal_to

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.alerts import (
    AlertEngine,
    FanoutSink,
    FileSink,
    LevelsUseCase,
    ListSink,
    NtfySink,
    format_alert,
    render_levels_csv,
    session_at,
)

ET = ZoneInfo("America/New_York")


def at(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=ET)


def engine_with_level(level=100.0, policy="regular"):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts, session_policy=policy)
    engine.set_levels({"AAA": level})
    return engine, alerts


class TestSessions(unittest.TestCase):
    def test_regular_pre_post_closed_weekday(self):
        assert_that(session_at(at(2026, 9, 22, 10, 0)), equal_to("regular"))
        assert_that(session_at(at(2026, 9, 22, 8, 0)), equal_to("pre"))
        assert_that(session_at(at(2026, 9, 22, 17, 0)), equal_to("post"))
        assert_that(session_at(at(2026, 9, 22, 21, 0)), equal_to("closed"))
        assert_that(session_at(at(2026, 9, 22, 3, 0)), equal_to("closed"))

    def test_weekends_closed(self):
        assert_that(session_at(at(2026, 9, 26, 12, 0)), equal_to("closed"))

    def test_dst_boundaries(self):
        # EDT (UTC-4): 9:30 open is 13:30Z; EST (UTC-5): 14:30Z.
        july_open = datetime(2026, 7, 1, 13, 30, tzinfo=ZoneInfo("UTC"))
        jan_open = datetime(2026, 1, 5, 14, 30, tzinfo=ZoneInfo("UTC"))
        assert_that(session_at(july_open), equal_to("regular"))
        assert_that(session_at(jan_open), equal_to("regular"))
        assert_that(session_at(datetime(2026, 7, 1, 13, 29, tzinfo=ZoneInfo("UTC"))), equal_to("pre"))


class TestEngineTransitions(unittest.TestCase):
    def test_first_below_tick_only_sets_baseline(self):
        engine, alerts = engine_with_level()

        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))

        assert_that(alerts.alerts, equal_to([]))
        assert_that(engine.armed["AAA"], equal_to(False))

    def test_above_then_below_fires_once(self):
        engine, alerts = engine_with_level()

        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 0))
        fired = engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 1))

        assert fired is not None
        assert_that(len(alerts.alerts), equal_to(1))
        assert_that(fired.symbol, equal_to("AAA"))
        assert_that(fired.session, equal_to("regular"))
        engine.on_tick("AAA", 98.0, at(2026, 9, 22, 10, 2))
        assert_that(len(alerts.alerts), equal_to(1))

    def test_rearm_above_then_fire_again(self):
        engine, alerts = engine_with_level()

        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 0))
        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 1))
        engine.on_tick("AAA", 102.0, at(2026, 9, 22, 10, 2))
        engine.on_tick("AAA", 99.5, at(2026, 9, 22, 10, 3))

        assert_that(len(alerts.alerts), equal_to(2))

    def test_opening_gap_cross_fires_when_seeded_above(self):
        engine, alerts = engine_with_level(level=100.0)
        engine.seed_baseline({"AAA": 105.0})

        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))

        assert_that(len(alerts.alerts), equal_to(1))

    def test_seeded_below_needs_a_recross(self):
        engine, alerts = engine_with_level(level=100.0)
        engine.seed_baseline({"AAA": 99.0})

        engine.on_tick("AAA", 98.0, at(2026, 9, 22, 10, 0))
        assert_that(alerts.alerts, equal_to([]))
        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 1))
        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 2))
        assert_that(len(alerts.alerts), equal_to(1))

    def test_pre_session_dip_is_labeled_ignored_not_silent(self):
        engine, alerts = engine_with_level()
        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 0))

        engine.on_tick("AAA", 99.0, at(2026, 9, 23, 8, 0))

        assert_that(alerts.alerts, equal_to([]))
        assert_that(len(engine.ignored), equal_to(1))
        ignored = engine.ignored[0]
        assert_that(ignored.session, equal_to("pre"))
        assert_that("regular-only" in ignored.reason, equal_to(True))
        assert_that(engine.armed["AAA"], equal_to(True))

    def test_extended_policy_fires_pre_with_session_label(self):
        engine, alerts = engine_with_level(policy="extended")
        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 0))

        fired = engine.on_tick("AAA", 99.0, at(2026, 9, 23, 8, 0))

        assert_that(fired is not None, equal_to(True))
        assert fired is not None
        assert_that(fired.session, equal_to("pre"))
        assert_that(len(engine.ignored), equal_to(0))

    def test_bad_session_policy_rejected(self):
        with self.assertRaises(ValueError):
            AlertEngine(on_alert=ListSink(), session_policy="always")


class TestDailyBarRecompute(unittest.TestCase):
    def test_new_bar_changes_level_and_ticks_compare_against_it(self):
        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)
        history = [100.0 * (1.001**i) for i in range(40)]
        engine.set_history("AAA", history, date(2026, 9, 21))
        old_level = engine.roll_daily_bar("AAA", history[-1] * 1.001, date(2026, 9, 21))
        assert_that(old_level is None, equal_to(True))
        engine.set_levels({"AAA": engine.levels.get("AAA", 95.0)})
        engine.seed_baseline({"AAA": history[-1]})

        new_level = engine.roll_daily_bar("AAA", 130.0, date(2026, 9, 22))

        assert new_level is not None
        # A tick between the old and new level must not fire.
        engine.on_tick("AAA", new_level + 1.0, at(2026, 9, 22, 10, 0))
        engine.on_tick("AAA", new_level - 0.5, at(2026, 9, 22, 10, 1))
        assert_that(len(alerts.alerts), equal_to(1))

    def test_level_move_reseeds_armed_state(self):
        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)
        history = [50.0] * 40
        engine.set_history("AAA", history, date(2026, 9, 21))
        engine.set_levels({"AAA": 48.0})
        engine.seed_baseline({"AAA": 49.0})

        engine.roll_daily_bar("AAA", 60.0, date(2026, 9, 22))

        assert_that(engine.armed["AAA"], equal_to(True))
        engine.on_tick("AAA", 40.0, at(2026, 9, 22, 10, 0))
        assert_that(len(alerts.alerts), equal_to(1))

    def test_dry_run_uses_prior_close_level_not_same_bar_close(self):
        from datetime import timedelta

        from mrmkt.indicator.risk_range import risk_range_series
        from mrmkt.usecase.alerts import dry_run_alerts

        closes = [100.0 * (1.001**i) for i in range(40)]
        dip_date = date(2026, 9, 22)
        # Prior-close level: history before the dip bar (seed + rolled bars).
        prior_level = risk_range_series(closes[:40], 15, 21, 0.5, 5)[-1].low
        dip_low = prior_level - 0.5
        dip_close = prior_level + 2.0
        closes = closes[:40] + [dip_close]
        days = [date(2026, 7, 27) + timedelta(days=i) for i in range(41)]
        bars = [
            SimpleNamespace(date=day, close=close, low=close * 0.999, high=close * 1.001)
            for day, close in zip(days, closes, strict=True)
        ]
        bars[-1] = SimpleNamespace(date=dip_date, close=dip_close, low=dip_low, high=dip_close)
        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)

        fired = dry_run_alerts(engine, {"AAA": bars})

        assert_that(len(fired), equal_to(1))
        assert_that(abs(fired[0].level - prior_level) < 1e-9, equal_to(True))

    def test_dry_run_first_replay_day_uses_seed_window_level(self):
        from datetime import timedelta

        from mrmkt.indicator.risk_range import risk_range_series
        from mrmkt.usecase.alerts import dry_run_alerts

        closes = [100.0 * (1.001**i) for i in range(31)]
        seed_level = risk_range_series(closes[:30], 15, 21, 0.5, 5)[-1].low
        days = [date(2026, 7, 27) + timedelta(days=i) for i in range(31)]
        bars = [
            SimpleNamespace(date=day, close=close, low=close, high=close)
            for day, close in zip(days, closes, strict=True)
        ]
        bars[-1] = SimpleNamespace(
            date=days[-1], close=closes[-1], low=seed_level - 1.0, high=closes[-1]
        )
        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)

        fired = dry_run_alerts(engine, {"AAA": bars})

        assert_that(len(fired), equal_to(1))
        assert_that(abs(fired[0].level - seed_level) < 1e-9, equal_to(True))


class TestStreamSource(unittest.TestCase):
    def test_exchange_timestamp_drives_session_not_receipt_time(self):
        from mrmkt.ext.alpaca_stream import AlpacaStreamSource

        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)
        engine.set_levels({"AAA": 100.0})
        engine.seed_baseline({"AAA": 105.0})
        received = []

        class StubStream:
            def subscribe_trades(self, handler, *symbols):
                self.trade_handler = handler

            def subscribe_daily_bars(self, handler, *symbols):
                self.bar_handler = handler

            def run(self):
                pass

        stream = StubStream()
        source = AlpacaStreamSource(
            stream, engine, lambda: at(2026, 9, 22, 10, 0)
        )
        source.start(["AAA"])
        # Exchange print at 08:00 pre-market; receipt clock says 10:00.
        trade = SimpleNamespace(
            symbol="AAA", price=99.0, timestamp=at(2026, 9, 22, 8, 0)
        )
        stream.trade_handler(trade)

        assert_that(alerts.alerts, equal_to([]))
        assert_that(len(engine.ignored), equal_to(1))
        assert_that(engine.ignored[0].session, equal_to("pre"))
        received.append(engine.ignored[0])

    def test_missing_trade_timestamp_falls_back_to_clock(self):
        from mrmkt.ext.alpaca_stream import AlpacaStreamSource

        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)
        engine.set_levels({"AAA": 100.0})
        engine.seed_baseline({"AAA": 105.0})

        class StubStream:
            def subscribe_trades(self, handler, *symbols):
                self.trade_handler = handler

            def subscribe_daily_bars(self, handler, *symbols):
                self.bar_handler = handler

            def run(self):
                pass

        stream = StubStream()
        AlpacaStreamSource(stream, engine, lambda: at(2026, 9, 22, 10, 0)).start(["AAA"])
        stream.trade_handler(SimpleNamespace(symbol="AAA", price=99.0, timestamp=None))

        assert_that(len(alerts.alerts), equal_to(1))


class TestSinks(unittest.TestCase):
    def test_fanout_and_file_sink(self):
        import tempfile

        alerts = ListSink()
        with tempfile.NamedTemporaryFile("r", suffix=".log") as tmp:
            fanout = FanoutSink([alerts, FileSink(tmp.name)])
            engine = AlertEngine(on_alert=fanout)
            engine.set_levels({"AAA": 100.0})
            engine.seed_baseline({"AAA": 105.0})
            engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))
            with open(tmp.name, encoding="utf-8") as handle:
                content = handle.read()

        assert_that(len(alerts.alerts), equal_to(1))
        assert_that("TRIGGER" in content, equal_to(True))
        assert_that("AAA" in content, equal_to(True))

    def test_format_alert_line(self):
        from mrmkt.usecase.alerts import Alert

        line = format_alert(
            Alert(
                symbol="CPAY",
                moment=at(2026, 9, 22, 10, 0),
                session="regular",
                price=390.0,
                level=390.07,
            )
        )

        assert_that("CPAY" in line and "TRIGGER" in line, equal_to(True))

    @requests_mock.Mocker()
    def test_ntfy_posts_raw_text_with_title_and_priority(self, mock):
        from mrmkt.usecase.alerts import Alert, NtfySink

        mock.post("https://ntfy.example/topic", text="ok")
        alert = Alert(
            symbol="CPAY",
            moment=at(2026, 9, 22, 10, 0),
            session="regular",
            price=390.0,
            level=390.07,
        )
        NtfySink("https://ntfy.example/topic")(alert)

        assert_that(mock.called, equal_to(True))
        request = mock.last_request
        assert_that(request.method, equal_to("POST"))
        assert_that(request.url, equal_to("https://ntfy.example/topic"))
        assert_that(request.text, equal_to(format_alert(alert)))
        assert_that(request.headers["Title"], equal_to("CPAY below risk-range buy 390.07"))
        assert_that(request.headers["Priority"], equal_to("4"))

    def test_ntfy_rejects_blank_url_and_non_http(self):
        with self.assertRaises(ValueError):
            NtfySink("")
        with self.assertRaises(ValueError):
            NtfySink("file:///tmp/alerts")

    @requests_mock.Mocker()
    def test_ntfy_failure_never_logs_topic(self, mock):
        import io
        from contextlib import redirect_stderr

        from mrmkt.usecase.alerts import Alert, NtfySink

        mock.post("https://ntfy.example/secret-topic", status_code=500, text="boom")
        err = io.StringIO()
        with redirect_stderr(err):
            NtfySink("https://ntfy.example/secret-topic")(
                Alert(
                    symbol="AAA",
                    moment=at(2026, 9, 22, 10, 0),
                    session="regular",
                    price=99.0,
                    level=100.0,
                )
            )

        assert_that("secret-topic" not in err.getvalue(), equal_to(True))
        assert_that("status=500" in err.getvalue(), equal_to(True))

    def test_build_sink_reads_ntfy_url_from_env_only(self):
        import os

        from mrmkt.cli import build_alert_sink

        os.environ.pop("MRMKT_ALERTS_NTFY_URL", None)
        with self.assertRaises(ValueError):
            build_alert_sink("ntfy")
        os.environ["MRMKT_ALERTS_NTFY_URL"] = "https://ntfy.example/topic"
        try:
            sink = build_alert_sink("ntfy")
            assert_that(isinstance(sink, NtfySink), equal_to(True))
        finally:
            os.environ.pop("MRMKT_ALERTS_NTFY_URL", None)

    def test_ntfy_url_resolution_prefers_env_then_config_spellings(self):
        from mrmkt.usecase.alerts import resolve_ntfy_url

        assert_that(
            resolve_ntfy_url("https://env.example/topic", {"ntfy": "https://cfg.example/other"}),
            equal_to("https://env.example/topic"),
        )
        assert_that(
            resolve_ntfy_url("", {"ntfy": "https://cfg.example/topic"}),
            equal_to("https://cfg.example/topic"),
        )
        assert_that(
            resolve_ntfy_url(None, {"nfty": "https://cfg.example/legacy"}),
            equal_to("https://cfg.example/legacy"),
        )
        assert_that(
            resolve_ntfy_url(None, {"nfty": "my-topic"}),
            equal_to("https://ntfy.sh/my-topic"),
        )
        assert_that(resolve_ntfy_url("", {}), equal_to(""))
        assert_that(resolve_ntfy_url(None, None), equal_to(""))


class TestLevelsUseCase(unittest.TestCase):
    def test_levels_are_deterministic(self):
        repo = InMemoryFinancialRepository()
        repo.add_ticker(Ticker(ticker="AAA", exchange="NASDAQ", type="us_equity"))
        price = 100.0
        day = date(2024, 1, 1)
        from datetime import timedelta

        for _ in range(40):
            while day.weekday() >= 5:
                day += timedelta(days=1)
            repo.add_price(
                StockPrice(
                    symbol="AAA",
                    date=day,
                    open=price,
                    high=price * 1.005,
                    low=price * 0.995,
                    close=price,
                    volume=1000.0,
                )
            )
            price *= 1.002
            day += timedelta(days=1)
        repo.add_tag("AAA", "NASDAQ", "universe")

        first = LevelsUseCase(repo).execute(include_tags=["universe"], symbols=[])
        second = LevelsUseCase(repo).execute(include_tags=["universe"], symbols=[])

        assert_that(len(first.rows), equal_to(1))
        assert_that(render_levels_csv(first), equal_to(render_levels_csv(second)))
        assert_that(first.rows[0].range_low < first.rows[0].close, equal_to(True))

    def test_explicit_symbols_never_fall_back_to_catalog(self):
        repo = InMemoryFinancialRepository()
        day = date(2024, 1, 1)
        from datetime import timedelta

        for symbol in ("AAA", "BBB"):
            repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
            price = 100.0
            cursor = day
            for _ in range(40):
                while cursor.weekday() >= 5:
                    cursor += timedelta(days=1)
                repo.add_price(
                    StockPrice(
                        symbol=symbol,
                        date=cursor,
                        open=price,
                        high=price * 1.005,
                        low=price * 0.995,
                        close=price,
                        volume=1000.0,
                    )
                )
                price *= 1.002
                cursor += timedelta(days=1)

        result = LevelsUseCase(repo).execute(include_tags=[], symbols=["AAA"])

        assert_that([r.symbol for r in result.rows], equal_to(["AAA"]))

    def test_empty_selection_returns_nothing(self):
        repo = InMemoryFinancialRepository()
        repo.add_ticker(Ticker(ticker="AAA", exchange="NASDAQ", type="us_equity"))
        repo.add_price(
            StockPrice(
                symbol="AAA",
                date=date(2024, 1, 1),
                open=100.0,
                high=100.5,
                low=99.5,
                close=100.0,
                volume=1000.0,
            )
        )

        result = LevelsUseCase(repo).execute(include_tags=[], symbols=[])

        assert_that(result.rows, equal_to([]))

    def test_tag_selection_stays_within_tags(self):
        repo = InMemoryFinancialRepository()
        day = date(2024, 1, 1)
        from datetime import timedelta

        for symbol, price in (("AAA", 100.0), ("BBB", 100.0), ("CCC", 200.0)):
            repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
            cursor = day
            for _ in range(40):
                while cursor.weekday() >= 5:
                    cursor += timedelta(days=1)
                repo.add_price(
                    StockPrice(
                        symbol=symbol,
                        date=cursor,
                        open=price,
                        high=price * 1.005,
                        low=price * 0.995,
                        close=price,
                        volume=1000.0,
                    )
                )
                price *= 1.002
                cursor += timedelta(days=1)
            if symbol in ("AAA", "BBB"):
                repo.add_tag(symbol, "NASDAQ", "idx")

        result = LevelsUseCase(repo).execute(include_tags=["idx"], symbols=[])

        assert_that(sorted(r.symbol for r in result.rows), equal_to(["AAA", "BBB"]))

    def test_watch_subscription_covers_exactly_selected_symbols(self):
        from mrmkt.ext.alpaca_stream import AlpacaStreamSource

        subscribed: dict = {}

        class StubStream:
            def subscribe_trades(self, handler, *symbols):
                subscribed["trades"] = symbols

            def subscribe_daily_bars(self, handler, *symbols):
                subscribed["bars"] = symbols

            def run(self):
                pass

        alerts = ListSink()
        engine = AlertEngine(on_alert=alerts)
        AlpacaStreamSource(StubStream(), engine, lambda: None).start(["AAA", "BBB"])

        assert_that(list(subscribed["trades"]), equal_to(["AAA", "BBB"]))
        assert_that(list(subscribed["bars"]), equal_to(["AAA", "BBB"]))

    def test_watch_dry_run_scores_only_selected_symbols(self):
        from typer.testing import CliRunner

        import mrmkt.cli as cli
        from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository as InMem

        repo = InMem()
        day = date(2024, 1, 1)
        from datetime import timedelta

        # AAA gets a dip that crosses the risk-range buy level.
        repo.add_ticker(Ticker(ticker="AAA", exchange="NASDAQ", type="us_equity"))
        closes_aaa = [100.0 * (1.002**i) for i in range(40)]
        for pos in (35, 36, 37):
            closes_aaa[pos] *= 0.90
        cursor = day
        for i, close in enumerate(closes_aaa):
            while cursor.weekday() >= 5:
                cursor += timedelta(days=1)
            low = close * 0.99 if i not in (35, 36, 37) else close * 0.95
            repo.add_price(
                StockPrice(
                    symbol="AAA",
                    date=cursor,
                    open=close,
                    high=close * 1.005,
                    low=low,
                    close=close,
                    volume=1000.0,
                )
            )
            cursor += timedelta(days=1)
        # BBB has too few bars for levels (< MIN_BARS).
        repo.add_ticker(Ticker(ticker="BBB", exchange="NASDAQ", type="us_equity"))
        price_bbb = 100.0
        cursor_bbb = day
        for _ in range(5):
            while cursor_bbb.weekday() >= 5:
                cursor_bbb += timedelta(days=1)
            repo.add_price(
                StockPrice(
                    symbol="BBB",
                    date=cursor_bbb,
                    open=price_bbb,
                    high=price_bbb * 1.005,
                    low=price_bbb * 0.995,
                    close=price_bbb,
                    volume=1000.0,
                )
            )
            price_bbb *= 1.002
            cursor_bbb += timedelta(days=1)
        original_factory = cli.create_local_ticker_repository
        cli.create_local_ticker_repository = lambda: (repo, lambda: None)
        try:
            result = CliRunner().invoke(cli.app, ["watch", "AAA", "BBB", "--dry-run"])
        finally:
            cli.create_local_ticker_repository = original_factory

        assert_that(result.exit_code, equal_to(0))
        assert_that("AAA" in result.output, equal_to(True))
        assert_that("BBB" not in result.output, equal_to(True))
