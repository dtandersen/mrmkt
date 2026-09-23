"""Volatility-implied probable trading ranges (Hedgeye Risk Range proxy).

The low end of the range is the buy/add level, the top end is the
sell/trim level. Range width scales with recent realized volatility and
the square root of the horizon, so targets adapt: high-volatility names
demand bigger pullbacks before triggering a buy.
"""

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class RiskRange:
    low: float
    high: float


def risk_range_series(
    prices: Sequence[float],
    horizon_days: int,
    vol_period: int = 21,
    width: float = 1.5,
) -> list[RiskRange]:
    """Return one volatility-implied range per bar.

    Each range is centered on that bar's close with half-width
    ``width * daily_vol * sqrt(horizon_days)`` as a fraction of price,
    where ``daily_vol`` is the sample deviation of log returns over the
    trailing ``vol_period`` returns. The first range aligns with
    ``prices[vol_period]``; fewer than ``vol_period + 1`` prices yields [].
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")
    if vol_period < 2:
        raise ValueError("vol_period must be at least 2")
    if width <= 0:
        raise ValueError("width must be positive")
    if any(price <= 0 for price in prices):
        raise ValueError("risk ranges require positive prices")
    if len(prices) < vol_period + 1:
        return []

    horizon_scale = math.sqrt(horizon_days)
    ranges = []
    for end in range(vol_period, len(prices)):
        window = prices[end - vol_period : end + 1]
        returns = [
            math.log(window[index + 1] / window[index])
            for index in range(vol_period)
        ]
        daily_vol = statistics.stdev(returns)
        half_width = width * daily_vol * horizon_scale
        center = prices[end]
        ranges.append(
            RiskRange(low=center * (1 - half_width), high=center * (1 + half_width))
        )
    return ranges
