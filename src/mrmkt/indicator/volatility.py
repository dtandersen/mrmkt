from collections.abc import Sequence
from math import log, sqrt
from statistics import stdev


def volatility(prices: Sequence[float], period: int, periods_per_year: int = 252) -> list[float]:
    """Return annualized rolling sample volatility of log price returns.

    A value is produced for each window of ``period`` daily returns, using
    sample standard deviation (ddof=1) scaled by ``sqrt(periods_per_year)``.
    Results are fractional annualized volatility, not percentages.
    """
    if period < 2:
        raise ValueError("period must be at least 2 returns")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if any(price <= 0 for price in prices):
        raise ValueError("prices must be positive")

    returns = [log(prices[index + 1] / prices[index]) for index in range(len(prices) - 1)]
    scale = sqrt(periods_per_year)
    return [
        stdev(returns[index : index + period]) * scale
        for index in range(len(returns) - period + 1)
    ]


def volatility_of_volatility(
    prices: Sequence[float],
    volatility_period: int,
    vol_of_vol_period: int,
    periods_per_year: int = 252,
) -> list[float]:
    """Return rolling sample deviation of log changes in realized volatility.

    The volatility series is annualized first. Volatility-of-volatility is the
    unannualized sample standard deviation of its log changes.
    """
    if vol_of_vol_period < 2:
        raise ValueError("vol_of_vol_period must be at least 2")

    vol_series = volatility(prices, volatility_period, periods_per_year)
    if len(vol_series) < vol_of_vol_period + 1:
        return []
    if any(value <= 0 for value in vol_series):
        raise ValueError("volatility-of-volatility requires positive volatility values")

    log_changes = [log(vol_series[index] / vol_series[index - 1]) for index in range(1, len(vol_series))]
    return [
        stdev(log_changes[index : index + vol_of_vol_period])
        for index in range(len(log_changes) - vol_of_vol_period + 1)
    ]


def rolling_percentile_rank(values: Sequence[float], lookback: int) -> list[float]:
    """Rank each value against the preceding ``lookback`` observations.

    The current observation is excluded from its reference window. Ties use
    mid-rank, and results are on a 0-100 scale.
    """
    if lookback < 1:
        raise ValueError("lookback must be positive")

    ranks = []
    for index in range(lookback, len(values)):
        history = values[index - lookback : index]
        current = values[index]
        tolerance = 1e-12 * max(1.0, abs(current))
        below = sum(value < current - tolerance for value in history)
        tied = sum(abs(value - current) <= tolerance for value in history)
        ranks.append((below + tied / 2) / lookback * 100)
    return ranks


def volatility_percentile(
    prices: Sequence[float],
    period: int,
    lookback: int = 252,
    periods_per_year: int = 252,
) -> list[float]:
    """Return each realized-volatility value's trailing historical percentile."""
    return rolling_percentile_rank(volatility(prices, period, periods_per_year), lookback)


def volatility_of_volatility_percentile(
    prices: Sequence[float],
    volatility_period: int,
    vol_of_vol_period: int,
    lookback: int = 252,
    periods_per_year: int = 252,
) -> list[float]:
    """Return each vol-of-vol value's trailing historical percentile."""
    values = volatility_of_volatility(
        prices,
        volatility_period,
        vol_of_vol_period,
        periods_per_year,
    )
    return rolling_percentile_rank(values, lookback)
