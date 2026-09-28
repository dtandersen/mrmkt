"""Tiingo fundamentals adapter (outer layer, ``mrmkt.ext``).

Batch ``get_fundamentals`` interface mirroring :class:`TiingoPriceSource`
so the ``ImportFundamentals`` command can select symbols the same way.
The API key comes from the ``TIINGO_API_KEY`` environment variable;
tests inject a stub ``client`` instead of touching the network.

Tiingo fundamentals split across two endpoints: ``statements`` (called
with ``asReported=true``, filing-date granularity matching legacy FMP
behavior) carries income/balance/cash-flow dataCodes plus per-filing
``sharesBasic``, while ``daily`` carries per-day ``marketCap``.
Translation from dataCodes to entities lives here so commands never
import this module (commands depend on repository interfaces only).

Verified dataCode mapping (``get_fundamentals_definitions``, 85 codes)::

    income:  netinc -> netIncome, shareswaDil (fallback shareswa) -> waso,
             consolidatedIncome -> consolidated_net_income
    balance: totalAssets, totalLiabilities, assetsNonCurrent
             (total non-current: totalAssets == assetsCurrent +
             assetsNonCurrent exactly for AAPL/MSFT/JNJ), inventory,
             acctRec -> receivables
    cash:    ncfo -> operating_cash_flow, capex, freeCashFlow,
             payDiv -> dividend_payments (Tiingo-negative values stored
             as-is), depamor -> deprec
    EV:      sharesBasic (per filing) + daily marketCap; price comes from
             stored bars (latest close on or before the daily date,
             resolved by the command, never from Tiingo).

A statement section missing a required code is skipped, never zero-filled.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from mrmkt.command.base import Log
from mrmkt.common.util import to_date
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.income_statement import IncomeStatement

TIINGO_API_KEY_ENV_VAR = "TIINGO_API_KEY"


@dataclass
class DailyMarketCap:
    """One daily market-cap point (Tiingo ``daily`` endpoint)."""

    date: date
    market_cap: float


@dataclass
class SymbolFundamentals:
    """Translated fundamentals for one symbol (statements + daily caps).

    Enterprise-value rows are assembled by the command, which joins
    ``shares_by_date`` (latest filing on or before each daily date) with
    ``daily_caps`` and stored bar closes.
    """

    symbol: str
    incomes: list[IncomeStatement] = field(default_factory=list)
    balances: list[BalanceSheet] = field(default_factory=list)
    cashflows: list[CashFlow] = field(default_factory=list)
    shares_by_date: dict[date, float] = field(default_factory=dict)
    daily_caps: list[DailyMarketCap] = field(default_factory=list)


class TiingoFundamentalsSource:
    """Fetch as-reported statements plus daily market caps from Tiingo."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client=None,
        log: Log,
    ):
        key = api_key if api_key is not None else os.environ.get(TIINGO_API_KEY_ENV_VAR)
        if client is None and not key:
            raise ValueError(
                f"{TIINGO_API_KEY_ENV_VAR} environment variable is not set"
            )
        self.api_key = key
        if client is not None:
            self.client = client
        else:
            from tiingo import TiingoClient

            self.client = TiingoClient({"api_key": key})
        self.log = log

    @classmethod
    def from_env(cls, log: Log, *, client=None) -> TiingoFundamentalsSource:
        """Build a source from the ``TIINGO_API_KEY`` environment variable."""
        return cls(api_key=None, client=client, log=log)

    def get_fundamentals(
        self, symbols: list[str], end: date
    ) -> dict[str, SymbolFundamentals]:
        """Return translated fundamentals for a batch of symbols.

        ``end`` bounds the daily market-cap history (statements always
        fetch the full filing history).
        """
        normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        if not normalized_symbols:
            return {}

        self.log("Connected to Tiingo fundamentals")
        self.log(f"Subscribing to {', '.join(normalized_symbols)}")

        return {
            symbol: self._get_symbol_fundamentals(symbol, end)
            for symbol in normalized_symbols
        }

    def _get_symbol_fundamentals(self, symbol: str, end: date) -> SymbolFundamentals:
        statements = self.client.get_fundamentals_statements(symbol, asReported=True)
        daily = self.client.get_fundamentals_daily(symbol, endDate=end.isoformat())
        return build_symbol_fundamentals(symbol, statements, daily)


def build_symbol_fundamentals(
    symbol: str, statements: Any, daily_rows: Any
) -> SymbolFundamentals:
    """Translate raw Tiingo payloads into entities (pure, no network)."""
    bundle = SymbolFundamentals(symbol=symbol)
    for statement in statements or []:
        try:
            filing_date = to_date(str(statement.get("date", ""))[:10])
        except ValueError:
            continue
        sections = statement.get("statementData", {}) or {}
        income = to_income(symbol, filing_date, sections.get("incomeStatement") or [])
        if income is not None:
            bundle.incomes.append(income)
        balance = to_balance(symbol, filing_date, sections.get("balanceSheet") or [])
        if balance is not None:
            bundle.balances.append(balance)
        cashflow = to_cash_flow(symbol, filing_date, sections.get("cashFlow") or [])
        if cashflow is not None:
            bundle.cashflows.append(cashflow)
        shares = _code_map(sections.get("balanceSheet") or []).get("sharesBasic")
        if shares is not None:
            bundle.shares_by_date[filing_date] = float(shares)
    for row in daily_rows or []:
        try:
            when = to_date(str(row.get("date", ""))[:10])
        except ValueError:
            continue
        market_cap = row.get("marketCap")
        if market_cap is None:
            continue
        bundle.daily_caps.append(
            DailyMarketCap(date=when, market_cap=float(market_cap))
        )
    bundle.incomes.sort(key=lambda item: item.date)
    bundle.balances.sort(key=lambda item: item.date)
    bundle.cashflows.sort(key=lambda item: item.date)
    bundle.daily_caps.sort(key=lambda item: item.date)
    return bundle


def _code_map(rows: Any) -> dict[str, float]:
    """Index ``[{dataCode, value}]`` rows by code, dropping nulls."""
    values: dict[str, float] = {}
    for row in rows:
        code = row.get("dataCode")
        value = row.get("value")
        if code is None or value is None:
            continue
        values[code] = float(value)
    return values


def to_income(symbol: str, filing_date: date, rows: Any) -> IncomeStatement | None:
    """Map income-statement rows; None when ``netinc`` is absent."""
    values = _code_map(rows)
    if "netinc" not in values:
        return None
    if "shareswaDil" in values:
        waso = int(values["shareswaDil"])
    elif "shareswa" in values:
        waso = int(values["shareswa"])
    else:
        waso = 0
    return IncomeStatement(
        symbol=symbol,
        date=filing_date,
        netIncome=values["netinc"],
        waso=waso,
        consolidated_net_income=values.get("consolidatedIncome", -1),
    )


def to_balance(symbol: str, filing_date: date, rows: Any) -> BalanceSheet | None:
    """Map balance-sheet rows; None without total assets and liabilities."""
    values = _code_map(rows)
    if "totalAssets" not in values or "totalLiabilities" not in values:
        return None
    return BalanceSheet(
        symbol=symbol,
        date=filing_date,
        totalAssets=values["totalAssets"],
        totalLiabilities=values["totalLiabilities"],
        non_current_assets=values.get("assetsNonCurrent", -1),
        inventories=values.get("inventory", -1),
        receivables=values.get("acctRec", -1),
    )


def to_cash_flow(symbol: str, filing_date: date, rows: Any) -> CashFlow | None:
    """Map cash-flow rows; None when a required flow code is absent."""
    values = _code_map(rows)
    required = ("ncfo", "capex", "freeCashFlow", "payDiv")
    if any(code not in values for code in required):
        return None
    return CashFlow(
        symbol=symbol,
        date=filing_date,
        operating_cash_flow=values["ncfo"],
        capital_expenditure=values["capex"],
        free_cash_flow=values["freeCashFlow"],
        dividend_payments=values["payDiv"],
        deprec=values.get("depamor", 0),
    )
