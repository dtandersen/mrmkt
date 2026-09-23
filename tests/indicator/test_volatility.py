import math
import unittest

from hamcrest import assert_that, close_to, equal_to, has_length

from mrmkt.indicator.volatility import (
    rolling_percentile_rank,
    volatility,
    volatility_of_volatility,
    volatility_of_volatility_percentile,
    volatility_percentile,
)


def prices_from_log_returns(log_returns):
    prices = [100.0]
    for log_return in log_returns:
        prices.append(prices[-1] * math.exp(log_return))
    return prices


class TestVolatility(unittest.TestCase):
    def test_annualizes_sample_deviation_of_log_returns(self):
        result = volatility(prices_from_log_returns([0.1, 0.0]), period=2)

        assert_that(result, has_length(1))
        assert_that(result[0], close_to(math.sqrt(1.26), 1e-12))

    def test_returns_one_value_per_rolling_window(self):
        result = volatility(
            prices_from_log_returns([0.1, 0.0, 0.2, 0.1]),
            period=2,
        )

        assert_that(result, has_length(3))
        assert_that(result[0], close_to(math.sqrt(1.26), 1e-12))
        assert_that(result[1], close_to(math.sqrt(5.04), 1e-12))
        assert_that(result[2], close_to(math.sqrt(1.26), 1e-12))

    def test_supports_fast_medium_and_slow_windows(self):
        prices = prices_from_log_returns([((index % 7) - 3) * 0.001 for index in range(252)])

        for period in (5, 21, 63):
            with self.subTest(period=period):
                assert_that(volatility(prices, period), has_length(252 - period + 1))

    def test_returns_empty_when_there_are_not_enough_returns(self):
        assert_that(volatility([100.0, 101.0], period=2), equal_to([]))

    def test_rejects_period_less_than_two(self):
        with self.assertRaises(ValueError):
            volatility([100.0, 101.0], 1)

    def test_rejects_non_positive_prices(self):
        with self.assertRaises(ValueError):
            volatility([100.0, 0.0, 101.0], 2)


class TestVolatilityOfVolatility(unittest.TestCase):
    def test_calculates_stddev_of_log_changes_in_annualized_volatility(self):
        prices = prices_from_log_returns([0.1, 0.0, 0.2, 0.1])

        result = volatility_of_volatility(
            prices,
            volatility_period=2,
            vol_of_vol_period=2,
        )

        assert_that(result, has_length(1))
        assert_that(result[0], close_to(math.sqrt(2) * math.log(2), 1e-12))

    def test_supports_fast_medium_and_slow_windows(self):
        prices = prices_from_log_returns([((index % 7) - 3) * 0.001 for index in range(252)])

        for period in (5, 21, 63):
            with self.subTest(period=period):
                assert_that(
                    volatility_of_volatility(prices, period, period),
                    has_length(252 - 2 * period + 1),
                )

    def test_returns_empty_when_there_are_too_few_volatility_values(self):
        assert_that(
            volatility_of_volatility([100.0, 101.0, 102.0], 2, 2),
            equal_to([]),
        )

    def test_rejects_zero_realized_volatility(self):
        with self.assertRaises(ValueError):
            volatility_of_volatility([100.0, 100.0, 100.0, 100.0, 100.0], 2, 2)

    def test_rejects_vol_of_vol_period_less_than_two(self):
        with self.assertRaises(ValueError):
            volatility_of_volatility([100.0, 101.0, 102.0], 2, 1)


class TestIndicatorPercentiles(unittest.TestCase):
    def test_rolling_percentile_uses_prior_values_and_midrank_for_ties(self):
        assert_that(rolling_percentile_rank([1.0, 2.0, 3.0, 2.0], 3), equal_to([50.0]))

    def test_volatility_percentile_ranks_against_prior_volatility_values(self):
        prices = prices_from_log_returns([0.1, 0.0, 0.2, 0.1])
        result = volatility_percentile(prices, period=2, lookback=2)

        assert_that(result, has_length(1))
        assert_that(result[0], close_to(25.0, 1e-12))

    def test_vol_of_vol_percentile_ranks_against_prior_values(self):
        prices = prices_from_log_returns([0.1, 0.0, 0.2, 0.1, 0.3, 0.0])
        result = volatility_of_volatility_percentile(
            prices,
            volatility_period=2,
            vol_of_vol_period=2,
            lookback=2,
        )

        assert_that(result, has_length(1))
        assert_that(result[0], close_to(0.0, 1e-12))

    def test_rejects_non_positive_lookback(self):
        with self.assertRaises(ValueError):
            rolling_percentile_rank([1.0, 2.0], 0)
