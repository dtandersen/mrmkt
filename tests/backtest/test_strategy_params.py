"""Unit tests for strategy param exposure, parsing, and building."""

import unittest

from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import (
    BuyRedStrategy,
    STRATEGIES,
    SmaCrossStrategy,
    build_strategy,
    register,
)


class TestParamSpecs(unittest.TestCase):
    def test_buy_red_specs_cover_backtest_params(self):
        specs = BuyRedStrategy.param_specs()

        assert_that(specs["width"].default, equal_to(0.5))
        assert_that(specs["use_vov"].default, equal_to(True))
        assert_that(specs["trend_fast"].default, equal_to(63))
        assert_that(bool(specs["width"].help), equal_to(True))

    def test_sma_cross_specs(self):
        specs = SmaCrossStrategy.param_specs()

        assert_that(specs["fast_period"].default, equal_to(50))
        assert_that(specs["slow_period"].default, equal_to(200))


class TestBuildStrategy(unittest.TestCase):
    def test_defaults_when_no_overrides(self):
        strategy = build_strategy("buy-red", {})

        assert isinstance(strategy, BuyRedStrategy)
        assert_that(strategy.params.width, equal_to(0.5))

    def test_coerces_int_float_and_bool(self):
        strategy = build_strategy(
            "buy-red",
            {"width": "1.0", "trend_fast": "20", "use_vov": "false"},
        )

        assert isinstance(strategy, BuyRedStrategy)
        assert_that(strategy.params.width, equal_to(1.0))
        assert_that(strategy.params.trend_fast, equal_to(20))
        assert_that(strategy.params.use_vov, equal_to(False))

    def test_builds_sma_cross(self):
        strategy = build_strategy("sma-cross", {"fast_period": "20"})

        assert isinstance(strategy, SmaCrossStrategy)
        assert_that(strategy.fast_period, equal_to(20))
        assert_that(strategy.slow_period, equal_to(200))

    def test_unknown_strategy_names_valid_choices(self):
        with self.assertRaises(ValueError) as ctx:
            build_strategy("nope", {})

        assert_that("buy-red" in str(ctx.exception), equal_to(True))

    def test_unknown_param_names_valid_keys(self):
        with self.assertRaises(ValueError) as ctx:
            build_strategy("sma-cross", {"bogus": "1"})

        assert_that("fast_period" in str(ctx.exception), equal_to(True))

    def test_bad_values_name_the_param(self):
        with self.assertRaises(ValueError) as ctx:
            build_strategy("buy-red", {"width": "wide"})

        assert_that("width" in str(ctx.exception), equal_to(True))

    def test_constructor_validation_still_applies(self):
        with self.assertRaises(ValueError):
            build_strategy("sma-cross", {"fast_period": "200", "slow_period": "50"})


class TestRegister(unittest.TestCase):
    def test_duplicate_registration_raises_without_clobbering(self):
        with self.assertRaises(ValueError):
            register("buy-red")(SmaCrossStrategy)

        assert_that(STRATEGIES["buy-red"], equal_to(BuyRedStrategy))
