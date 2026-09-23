import unittest

from hamcrest import assert_that, close_to, equal_to, has_length

from mrmkt.indicator.risk_range import RiskRange, risk_range_series


class TestRiskRange(unittest.TestCase):
    def test_anchors_range_on_trailing_mean_after_a_rip(self):
        ranges = risk_range_series(
            [100.0, 100.0, 100.0, 130.0], 1,
            vol_period=2, width=1.0, anchor_period=2,
        )

        assert_that(ranges, has_length(2))
        assert_that(ranges[0], equal_to(RiskRange(low=100.0, high=100.0)))
        assert_that(ranges[1].low, close_to(93.665252, 1e-6))
        assert_that(ranges[1].high, close_to(136.334748, 1e-6))
        assert_that(ranges[1].low < 100.0, equal_to(True))

    def test_flat_prices_collapse_to_the_close(self):
        ranges = risk_range_series([100.0, 100.0, 100.0], 15, vol_period=2, anchor_period=1)

        assert_that(ranges, has_length(1))
        assert_that(ranges[0], equal_to(RiskRange(low=100.0, high=100.0)))

    def test_half_width_scales_linearly_with_width(self):
        narrow = risk_range_series([100.0, 110.0, 100.0], 1, vol_period=2, width=1.0, anchor_period=1)
        wide = risk_range_series([100.0, 110.0, 100.0], 1, vol_period=2, width=2.0, anchor_period=1)

        assert_that(100.0 - wide[0].low, close_to(2 * (100.0 - narrow[0].low), 1e-9))
        assert_that(wide[0].high - 100.0, close_to(2 * (narrow[0].high - 100.0), 1e-9))

    def test_half_width_scales_with_square_root_of_horizon(self):
        short = risk_range_series([100.0, 110.0, 100.0], 1, vol_period=2, anchor_period=1)
        long = risk_range_series([100.0, 110.0, 100.0], 4, vol_period=2, anchor_period=1)

        assert_that(100.0 - long[0].low, close_to(2 * (100.0 - short[0].low), 1e-9))

    def test_returns_empty_when_history_is_shorter_than_vol_window(self):
        assert_that(risk_range_series([100.0, 110.0], 15, vol_period=2), equal_to([]))

    def test_rejects_bad_parameters(self):
        with self.assertRaises(ValueError):
            risk_range_series([100.0, 110.0, 100.0], 0)
        with self.assertRaises(ValueError):
            risk_range_series([100.0, 110.0, 100.0], 15, vol_period=1)
        with self.assertRaises(ValueError):
            risk_range_series([100.0, 110.0, 100.0], 15, width=0.0)

    def test_rejects_non_positive_prices(self):
        with self.assertRaises(ValueError):
            risk_range_series([100.0, 0.0, 100.0], 15, vol_period=2)
