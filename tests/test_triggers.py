"""Unit tests for stored triggers: engine operators/frequencies/expiry/templates and the repository."""

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from hamcrest import assert_that, equal_to

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.trigger import Trigger
from mrmkt.usecase.alerts import (
    AlertEngine,
    ListSink,
    TriggerRule,
    format_alert,
    render_message,
)

ET = ZoneInfo("America/New_York")


def at(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=ET)


def engine_with_rule(rule, level=100.0, prior=105.0):
    alerts = ListSink()
    engine = AlertEngine(on_alert=alerts)
    engine.set_levels({"AAA": level})
    engine.set_rule("AAA", rule)
    engine.seed_baseline({"AAA": prior})
    return engine, alerts


class TestOperators(unittest.TestCase):
    def test_crossing_up_fires_on_rise_through(self):
        engine, alerts = engine_with_rule(TriggerRule(operator="crossing-up"), prior=95.0)

        assert_that(engine.armed["AAA"], equal_to(True))
        engine.on_tick("AAA", 94.0, at(2026, 9, 22, 10, 0))
        assert_that(alerts.alerts, equal_to([]))
        fired = engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 1))

        assert fired is not None
        assert_that(len(alerts.alerts), equal_to(1))

    def test_crossing_up_seed_above_needs_recross(self):
        engine, alerts = engine_with_rule(TriggerRule(operator="crossing-up"), prior=105.0)

        engine.on_tick("AAA", 106.0, at(2026, 9, 22, 10, 0))
        assert_that(alerts.alerts, equal_to([]))
        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 1))
        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 2))
        assert_that(len(alerts.alerts), equal_to(1))

    def test_greater_than_every_time_fires_each_holding_tick(self):
        engine, alerts = engine_with_rule(
            TriggerRule(operator="greater-than", frequency="every_time"), prior=95.0
        )

        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 0))
        engine.on_tick("AAA", 102.0, at(2026, 9, 22, 10, 1))

        assert_that(len(alerts.alerts), equal_to(2))

    def test_less_than_once_per_rearm_needs_exit_to_rearm(self):
        engine, alerts = engine_with_rule(
            TriggerRule(operator="less-than", frequency="once_per_rearm"), prior=105.0
        )

        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))
        engine.on_tick("AAA", 98.0, at(2026, 9, 22, 10, 1))
        assert_that(len(alerts.alerts), equal_to(1))
        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 2))
        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 3))
        assert_that(len(alerts.alerts), equal_to(2))

    def test_bad_rule_rejected(self):
        engine = AlertEngine(on_alert=ListSink())

        with self.assertRaises(ValueError):
            engine.set_rule("AAA", TriggerRule(operator="sideways"))
        with self.assertRaises(ValueError):
            engine.set_rule("AAA", TriggerRule(frequency="sometimes"))


class TestFrequencyOnce(unittest.TestCase):
    def test_once_never_rearms(self):
        engine, alerts = engine_with_rule(TriggerRule(frequency="once"), prior=105.0)

        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))
        assert_that(len(alerts.alerts), equal_to(1))
        assert_that("AAA" in engine.spent, equal_to(True))
        engine.on_tick("AAA", 101.0, at(2026, 9, 22, 10, 1))
        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 2))
        assert_that(len(alerts.alerts), equal_to(1))


class TestExpiry(unittest.TestCase):
    def test_expired_trigger_never_fires_and_is_labeled(self):
        engine, alerts = engine_with_rule(
            TriggerRule(expires_at=date(2026, 9, 21)), prior=105.0
        )

        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))

        assert_that(alerts.alerts, equal_to([]))
        assert_that(len(engine.ignored), equal_to(1))
        assert_that(engine.ignored[0].reason, equal_to("trigger expired"))

    def test_unexpired_trigger_fires(self):
        engine, alerts = engine_with_rule(
            TriggerRule(expires_at=date(2026, 9, 22)), prior=105.0
        )

        engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))

        assert_that(len(alerts.alerts), equal_to(1))


class TestMessageTemplate(unittest.TestCase):
    def test_template_placeholders_render(self):
        text = render_message(
            "{symbol} broke {level:g} at {price:g} ({session} {moment})",
            symbol="CPAY",
            price=390.0,
            level=390.07,
            moment=at(2026, 9, 22, 10, 0),
            session="regular",
        )

        assert_that("CPAY" in text, equal_to(True))
        assert_that("390" in text, equal_to(True))

    def test_bad_template_falls_back_to_default_line(self):
        engine, alerts = engine_with_rule(
            TriggerRule(message="{nonexistent}"), prior=105.0
        )

        fired = engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))

        assert fired is not None
        assert_that("TRIGGER" in format_alert(fired), equal_to(True))

    def test_rule_message_reaches_alert_text(self):
        engine, alerts = engine_with_rule(
            TriggerRule(message="{symbol} ping"), prior=105.0
        )

        fired = engine.on_tick("AAA", 99.0, at(2026, 9, 22, 10, 0))

        assert fired is not None
        assert_that(fired.text, equal_to("AAA ping"))


class TestTriggerRepository(unittest.TestCase):
    def test_add_list_remove_round_trip(self):
        repo = InMemoryFinancialRepository()

        stored = repo.add_trigger(Trigger(id=None, symbol="AAA"))
        assert_that(stored.id, equal_to(1))
        assert_that(stored.operator, equal_to("crossing-down"))
        assert_that(stored.enabled, equal_to(True))

        listed = repo.list_triggers()
        assert_that([t.symbol for t in listed], equal_to(["AAA"]))

        assert_that(repo.set_trigger_enabled(1, False), equal_to(True))
        assert_that(repo.list_triggers(enabled_only=True), equal_to([]))
        assert_that(repo.set_trigger_enabled(1, True), equal_to(True))
        assert_that(len(repo.list_triggers(enabled_only=True)), equal_to(1))

        assert_that(repo.remove_trigger(1), equal_to(True))
        assert_that(repo.list_triggers(), equal_to([]))
        assert_that(repo.remove_trigger(1), equal_to(False))
        assert_that(repo.set_trigger_enabled(999, True), equal_to(False))

    def test_duplicate_and_validation_rejected(self):
        repo = InMemoryFinancialRepository()
        repo.add_trigger(Trigger(id=None, symbol="AAA"))

        with self.assertRaises(ValueError):
            repo.add_trigger(Trigger(id=None, symbol="AAA"))
        with self.assertRaises(ValueError):
            repo.add_trigger(Trigger(id=None, symbol="BBB", operator="sideways"))
        with self.assertRaises(ValueError):
            repo.add_trigger(Trigger(id=None, symbol="BBB", frequency="sometimes"))
        with self.assertRaises(ValueError):
            repo.add_trigger(Trigger(id=None, symbol="BBB", signal="rsi"))

    def test_same_symbol_different_operator_allowed(self):
        repo = InMemoryFinancialRepository()
        repo.add_trigger(Trigger(id=None, symbol="AAA", operator="crossing-down"))
        second = repo.add_trigger(Trigger(id=None, symbol="AAA", operator="crossing-up"))

        assert_that(second.id, equal_to(2))
        assert_that(len(repo.list_triggers()), equal_to(2))
