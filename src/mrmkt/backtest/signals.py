"""Entry/exit signal builders over wide (dates x symbols) OHLC frames."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestParams:
    width: float = 0.5
    vol_period: int = 21
    anchor_period: int = 5
    horizon_days: int = 15
    trend_fast: int = 63
    trend_slow: int = 200
    dist_lo_min: float = 0.10
    dd_max: float = 0.35
    vov_max: float = 30.0
    use_vov: bool = True
    vov_lookback: int = 252


def vov_percentile(close: pd.DataFrame, vol_period: int = 21, lookback: int = 252) -> pd.DataFrame:
    """21/21-style vol-of-vol percentile rank per symbol (0-100)."""
    logret = np.log(close / close.shift(1))
    dvol = logret.rolling(vol_period).std(ddof=1)
    vol = dvol * np.sqrt(252)
    lch = np.log(vol / vol.shift(1))
    vov = lch.rolling(vol_period).std(ddof=1)
    out = pd.DataFrame(np.nan, index=vov.index, columns=vov.columns)
    window = lookback + 1
    for sym in vov.columns:
        col = np.r_[np.full(lookback, np.nan), vov[sym].to_numpy()]
        wins = np.lib.stride_tricks.sliding_window_view(col, window)
        with np.errstate(invalid="ignore"):
            rank = (wins[:, -1:] > wins[:, :-1]).sum(axis=1) / lookback * 100
        ok = (~np.isnan(wins)).sum(axis=1) == window
        out[sym] = np.where(ok, rank, np.nan)
    return out


def _levels(
    close: pd.DataFrame,
    params: BacktestParams,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sma_fast: pd.DataFrame = pd.DataFrame(close.rolling(params.trend_fast).mean())
    sma_slow: pd.DataFrame = pd.DataFrame(close.rolling(params.trend_slow).mean())
    anchor: pd.DataFrame = pd.DataFrame(close.rolling(params.anchor_period).mean())
    # np.log on a DataFrame returns a DataFrame (pandas __array_ufunc__);
    # the annotation pins that for the type checker.
    dvol: pd.DataFrame = np.log(close / close.shift(1)).rolling(params.vol_period).std(ddof=1)
    half_width = params.width * dvol * np.sqrt(params.horizon_days)
    buy: pd.DataFrame = anchor * (1 - half_width)
    sell: pd.DataFrame = anchor * (1 + half_width)
    trailing_low: pd.DataFrame = pd.DataFrame(close.rolling(params.vov_lookback).min())
    dist_lo: pd.DataFrame = (close - trailing_low) / trailing_low
    trailing_peak: pd.DataFrame = pd.DataFrame(
        close.rolling(params.vov_lookback, min_periods=1).max()
    )
    drawdown: pd.DataFrame = (close / trailing_peak - 1).rolling(params.vov_lookback, min_periods=1).min()
    return sma_fast, sma_slow, buy, sell, dist_lo, drawdown, dvol


def entry_signals(
    close: pd.DataFrame,
    low: pd.DataFrame,
    params: BacktestParams,
    vov: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """True where a long entry triggers: bullish TREND+TAIL, vetoes pass,
    daily low touches the TRADE buy level (plus VoV compression unless
    disabled or no ranking supplied)."""
    sma_fast, sma_slow, buy, _, dist_lo, drawdown, _ = _levels(close, params)
    valid = close.notna() & sma_slow.notna() & dist_lo.notna()
    entries = (
        valid
        & (close > sma_fast)
        & (close > sma_slow)
        & (dist_lo > params.dist_lo_min)
        & (drawdown > -params.dd_max)
        & (low <= buy)
    )
    if params.use_vov and vov is not None:
        entries &= vov <= params.vov_max
    return entries.fillna(False)


def exit_signals(
    close: pd.DataFrame,
    high: pd.DataFrame,
    params: BacktestParams,
) -> pd.DataFrame:
    """True where an open long exits: daily high reaches the
    contemporaneous range top, or close breaks TREND support."""
    sma_fast, _, _, sell, _, _, _ = _levels(close, params)
    valid = close.notna() & sma_fast.notna() & sell.notna()
    return (valid & ((high >= sell) | (close < sma_fast))).fillna(False)
