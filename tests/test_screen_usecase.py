"""Unit tests for the technical screener use case."""

import unittest
from datetime import date, timedelta

from hamcrest import assert_that, equal_to

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.screen import ScreenRequest, ScreenUseCase, render_csv

START = date(2022, 1, 3)


def business_days(start: date, n: int) -> list:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def add_climb(repo, symbol, n=250, start_price=100.0, drift=0.002, exchange="NASDAQ"):
    repo.add_ticker(Ticker(ticker=symbol, exchange=exchange, type="us_equity"))
    price = start_price
    for pos, day in enumerate(business_days(START, n)):
        if pos > 0:
            price *= 1 + drift
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=100000.0,
            )
        )


def repo_with_universe():
    repo = InMemoryFinancialRepository()
    add_climb(repo, "AAA", drift=0.003)
    add_climb(repo, "BBB", drift=0.001)
    add_climb(repo, "CCC", drift=-0.001)
    for symbol in ("AAA", "BBB", "CCC"):
        repo.add_tag(symbol, "NASDAQ", "universe")
    repo.add_tag("CCC", "NASDAQ", "junk")
    return repo


class TestScreenUniverse(unittest.TestCase):
    def test_include_and_exclude_tags(self):
        repo = repo_with_universe()

        result = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], exclude_tags=["junk"])
        )

        assert_that({r.symbol for r in result.rows}, equal_to({"AAA", "BBB"}))
        assert_that(result.universe_size, equal_to(2))

    def test_default_mode_is_technical_only(self):
        repo = repo_with_universe()

        result = ScreenUseCase(repo).execute(ScreenRequest(include_tags=["universe"]))

        assert_that(result.request.mode, equal_to("technical-only"))

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            ScreenUseCase(repo_with_universe()).execute(
                ScreenRequest(include_tags=["universe"], mode="fundamental")
            )

        assert_that("technical-only" in str(ctx.exception), equal_to(True))


class TestScreenAsOf(unittest.TestCase):
    def test_metrics_use_only_bars_on_or_before_as_of(self):
        repo = repo_with_universe()
        as_of = business_days(START, 250)[219]

        result = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], as_of=as_of)
        )

        assert_that(result.as_of, equal_to(as_of))
        assert_that(result.data_vintage, equal_to(as_of))
        for row in result.rows:
            assert_that(row.last_date <= as_of, equal_to(True))

    def test_vintage_spans_full_universe_before_top_n(self):
        repo = InMemoryFinancialRepository()
        # Top-ranked AAA goes stale early; low-ranked CCC holds the latest
        # bar. A post-truncation vintage would report AAA's stale date.
        add_climb(repo, "AAA", n=230, drift=0.003)
        add_climb(repo, "BBB", drift=0.001)
        add_climb(repo, "CCC", drift=-0.001)
        for symbol in ("AAA", "BBB", "CCC"):
            repo.add_tag(symbol, "NASDAQ", "universe")
        as_of = business_days(START, 250)[-1]

        top = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], as_of=as_of, top_n=1)
        )

        assert_that(len(top.rows), equal_to(1))
        assert_that(top.rows[0].symbol, equal_to("AAA"))
        assert_that(top.rows[0].last_date < as_of, equal_to(True))
        assert_that(top.data_vintage, equal_to(as_of))


class TestScreenFilters(unittest.TestCase):
    def test_exclusion_reasons_are_tracked_separately(self):
        repo = repo_with_universe()

        result = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], min_price=100000.0)
        )

        assert_that(result.rows, equal_to([]))
        assert_that(set(result.excluded), equal_to({"min_price"}))
        assert_that(sum(result.excluded.values()), equal_to(3))
        assert_that("# excluded_min_price=3" in render_csv(result), equal_to(True))

    def test_short_history_excluded(self):
        repo = InMemoryFinancialRepository()
        add_climb(repo, "SHORT", n=50)
        repo.add_tag("SHORT", "NASDAQ", "universe")

        result = ScreenUseCase(repo).execute(ScreenRequest(include_tags=["universe"]))

        assert_that(result.rows, equal_to([]))
        assert_that(result.excluded.get("short_history"), equal_to(1))

    def test_max_stale_days_is_opt_in(self):
        repo = repo_with_universe()
        as_of = business_days(START, 250)[-1] + timedelta(days=30)

        kept = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], as_of=as_of)
        )
        assert_that(len(kept.rows), equal_to(3))
        assert_that("stale" in kept.excluded, equal_to(False))

        gated = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], as_of=as_of, max_stale_days=5)
        )
        assert_that(gated.rows, equal_to([]))
        assert_that(gated.excluded.get("stale"), equal_to(3))
        assert_that("# max_stale_days=5" in render_csv(gated), equal_to(True))

    def test_csv_echoes_inputs_and_fixed_lookbacks(self):
        repo = repo_with_universe()
        result = ScreenUseCase(repo).execute(
            ScreenRequest(include_tags=["universe"], exclude_tags=["junk"], top_n=2)
        )
        text = render_csv(result)

        for needle in (
            "# mode=technical-only",
            "# universe_tags=universe",
            "# universe_exclude_tags=junk",
            "# universe_membership_vintage=current",
            "# excluded_total=",
            "sma_periods=20/63/200",
            "mom_lookback=126",
            "pullback_cap=0.10",
            "rank,symbol,last_date",
        ):
            assert_that(needle in text, equal_to(True))

    def test_csv_is_deterministic(self):
        repo = repo_with_universe()
        request = ScreenRequest(include_tags=["universe"])

        first = render_csv(ScreenUseCase(repo).execute(request))
        second = render_csv(ScreenUseCase(repo).execute(request))

        assert_that(second, equal_to(first))

    def test_scores_rank_best_first_with_symbol_tiebreak(self):
        repo = repo_with_universe()
        result = ScreenUseCase(repo).execute(ScreenRequest(include_tags=["universe"]))

        scores = [r.score for r in result.rows]
        assert_that(scores, equal_to(sorted(scores, reverse=True)))
        assert_that(result.rows[0].rank, equal_to(1))
