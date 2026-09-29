"""Tests for the accidental-peek audit of strategy generate() code."""

from pathlib import Path

from hamcrest import assert_that, empty, equal_to, has_length

from mrmkt.backtest.nopeek import audit_path, audit_source

STRATEGY_DIR = (
    Path(__file__).parent.parent.parent / "src" / "mrmkt" / "backtest" / "strategy"
)


def _rule_ids(findings):
    return [finding.rule for finding in findings]


def test_bundled_strategies_are_peek_free():
    for path in sorted(STRATEGY_DIR.glob("*.py")):
        assert_that(audit_path(str(path)), empty(), f"{path.name} must be peek-free")


def test_centered_rolling_window_is_flagged():
    findings = audit_source("x = close.rolling(20, center=True).mean()\n")

    assert_that(_rule_ids(findings), equal_to(["centered-window"]))


def test_negative_shift_is_flagged():
    findings = audit_source("past = close.shift(-21)\n")

    assert_that(_rule_ids(findings), equal_to(["negative-period"]))


def test_positive_shift_is_clean():
    assert_that(audit_source("past = close.shift(21)\n"), empty())


def test_keyword_negative_period_is_flagged():
    findings = audit_source("past = close.shift(periods=-21)\n")

    assert_that(_rule_ids(findings), equal_to(["negative-period"]))


def test_keyword_positive_period_is_clean():
    assert_that(audit_source("past = close.shift(periods=21)\n"), empty())


def test_default_axis_rank_is_flagged():
    findings = audit_source("rank = momentum.rank(pct=True)\n")

    assert_that(_rule_ids(findings), equal_to(["time-axis-rank"]))


def test_explicit_time_axis_rank_is_flagged():
    findings = audit_source("rank = momentum.rank(axis=0, pct=True)\n")

    assert_that(_rule_ids(findings), equal_to(["time-axis-rank"]))


def test_cross_sectional_rank_is_clean():
    assert_that(audit_source("rank = momentum.rank(axis=1, pct=True)\n"), empty())
    assert_that(audit_source('rank = momentum.rank(axis="columns")\n'), empty())


def test_string_index_axis_rank_is_flagged():
    findings = audit_source('rank = momentum.rank(axis="index")\n')

    assert_that(_rule_ids(findings), equal_to(["time-axis-rank"]))


def test_negative_pct_change_is_flagged():
    findings = audit_source("fwd = close.pct_change(-1)\n")

    assert_that(_rule_ids(findings), equal_to(["negative-period"]))


def test_multiple_violations_all_reported_with_lines():
    source = "a = close.shift(-1)\n\nb = close.rolling(5, center=True).mean()\n"
    findings = audit_source(source)

    assert_that(findings, has_length(2))
    assert_that([finding.lineno for finding in findings], equal_to([1, 3]))


def test_unparseable_source_reports_instead_of_raising():
    findings = audit_source("def broken(:\n")

    assert_that(_rule_ids(findings), equal_to(["unparseable"]))


def test_aliased_lookahead_is_flagged():
    findings = audit_source("shift = close.shift\nfuture = shift(-1)\n")

    assert_that(_rule_ids(findings), equal_to(["negative-period"]))


def test_aliased_benign_call_is_clean():
    findings = audit_source("shift = close.shift\npast = shift(21)\n")

    assert_that(findings, empty())
