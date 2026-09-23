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
    width: float = 0.5,
    anchor_period: int = 5,
) -> list[RiskRange]:
    """Return one volatility-implied range per bar.

    Each range is centered on the trailing ``anchor_period`` mean with
    half-width ``width * daily_vol * sqrt(horizon_days)`` as a fraction
    of the anchor, where ``daily_vol`` is the sample deviation of log
    returns over the trailing ``vol_period`` returns. Anchoring on a fast
    mean (rather than the latest close) keeps the range honest after
    sharp runs: an extended price sits near the top (sell/trim) instead
    of dragging the whole range with it. The first range aligns with
    ``prices[max(vol_period, anchor_period - 1)]``; shorter histories
    yield [].
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")
    if vol_period < 2:
        raise ValueError("vol_period must be at least 2")
    if width <= 0:
        raise ValueError("width must be positive")
    if anchor_period < 1:
        raise ValueError("anchor_period must be at least 1")
    if any(price <= 0 for price in prices):
        raise ValueError("risk ranges require positive prices")
    first = max(vol_period, anchor_period - 1)
    if len(prices) < first + 1:
        return []

    horizon_scale = math.sqrt(horizon_days)
    ranges = []
    for end in range(first, len(prices)):
        window = prices[end - vol_period : end + 1]
        returns = [
            math.log(window[index + 1] / window[index])
            for index in range(vol_period)
        ]
        daily_vol = statistics.stdev(returns)
        half_width = width * daily_vol * horizon_scale
        center = sum(prices[end - anchor_period + 1 : end + 1]) / anchor_period
        ranges.append(
            RiskRange(low=center * (1 - half_width), high=center * (1 + half_width))
        )
    return ranges
