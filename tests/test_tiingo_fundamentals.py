"""Unit tests for the Tiingo fundamentals adapter (no network).

A stub client serves canned statement/daily payloads shaped like the live
Tiingo responses (verified September 2026); translation and request
parameters are asserted without touching Tiingo or a database.
"""

import datetime
import os
from datetime import date

import pytest
from hamcrest import assert_that, contains_string, equal_to
from tests.fakes import CapturingLog

from mrmkt.ext.tiingo_fundamentals import (
    TIINGO_API_KEY_ENV_VAR,
    TiingoFundamentalsSource,
    build_symbol_fundamentals,
)


def _statement(filing_date, income=None, balance=None, cash=None):
    return {
        "date": filing_date,
        "year": 2024,
        "quarter": 1,
        "statementData": {
            "incomeStatement": income or [],
            "balanceSheet": balance or [],
            "cashFlow": cash or [],
            "overview": [],
        },
    }


def _row(code, value):
    return {"dataCode": code, "value": value}


def _full_bundle():
    income = [
        _row("netinc", 29789000000.0),
        _row("shareswaDil", 14714676000.0),
        _row("shareswa", 14656110000.0),
        _row("consolidatedIncome", 29789000000.0),
    ]
    balance = [
        _row("totalAssets", 383266000000.0),
        _row("totalLiabilities", 275746000000.0),
        _row("assetsNonCurrent", 233448000000.0),
        _row("assetsCurrent", 149818000000.0),
        _row("inventory", 11092000000.0),
        _row("acctRec", 58907000000.0),
        _row("sharesBasic", 14594180000.0),
    ]
    cash = [
        _row("ncfo", 34369000000.0),
        _row("capex", -2455000000.0),
        _row("freeCashFlow", 31914000000.0),
        _row("payDiv", -4035000000.0),
        _row("depamor", 3320000000.0),
    ]
    return _statement("2024-03-31", income, balance, cash)


def test_full_statement_maps_all_entities():
    bundle = build_symbol_fundamentals(
        "AAPL",
        [_full_bundle()],
        [{"date": "2024-04-01T00:00:00.000Z", "marketCap": 50000.0}],
    )

    (income,) = bundle.incomes
    assert_that(income.symbol, equal_to("AAPL"))
    assert_that(income.date, equal_to(date(2024, 3, 31)))
    assert_that(income.netIncome, equal_to(29789000000.0))
    assert_that(income.waso, equal_to(14714676000))
    assert_that(income.consolidated_net_income, equal_to(29789000000.0))

    (balance,) = bundle.balances
    assert_that(balance.totalAssets, equal_to(383266000000.0))
    assert_that(balance.totalLiabilities, equal_to(275746000000.0))
    assert_that(balance.non_current_assets, equal_to(233448000000.0))
    assert_that(balance.inventories, equal_to(11092000000.0))
    assert_that(balance.receivables, equal_to(58907000000.0))

    (flow,) = bundle.cashflows
    assert_that(flow.operating_cash_flow, equal_to(34369000000.0))
    assert_that(flow.capital_expenditure, equal_to(-2455000000.0))
    assert_that(flow.free_cash_flow, equal_to(31914000000.0))
    assert_that(flow.dividend_payments, equal_to(-4035000000.0))
    assert_that(flow.deprec, equal_to(3320000000.0))

    assert_that(bundle.shares_by_date, equal_to({date(2024, 3, 31): 14594180000.0}))
    assert_that(len(bundle.daily_caps), equal_to(1))
    assert_that(bundle.daily_caps[0].market_cap, equal_to(50000.0))


def test_diluted_shares_fall_back_to_basic_then_zero():
    rows = [_row("netinc", 1.0), _row("shareswa", 700.0)]
    (income,) = build_symbol_fundamentals(
        "AAA", [_statement("2024-03-31", income=rows)], []
    ).incomes
    assert_that(income.waso, equal_to(700))

    (income,) = build_symbol_fundamentals(
        "AAA", [_statement("2024-03-31", income=[_row("netinc", 1.0)])], []
    ).incomes
    assert_that(income.waso, equal_to(0))
    assert_that(income.consolidated_net_income, equal_to(-1))


def test_sections_missing_required_codes_are_skipped_never_zero_filled():
    bundle = build_symbol_fundamentals(
        "AAA",
        [
            _statement(
                "2024-03-31",
                income=[_row("shareswa", 5.0)],
                balance=[_row("totalAssets", 9.0)],
                cash=[_row("ncfo", 1.0), _row("capex", 2.0)],
            )
        ],
        [{"date": "2024-04-01T00:00:00.000Z"}],
    )
    assert_that(bundle.incomes, equal_to([]))
    assert_that(bundle.balances, equal_to([]))
    assert_that(bundle.cashflows, equal_to([]))
    assert_that(bundle.daily_caps, equal_to([]))


def test_optional_codes_keep_legacy_defaults():
    bundle = build_symbol_fundamentals(
        "AAA",
        [
            _statement(
                "2024-03-31",
                balance=[
                    _row("totalAssets", 9.0),
                    _row("totalLiabilities", 4.0),
                ],
                cash=[
                    _row("ncfo", 1.0),
                    _row("capex", 2.0),
                    _row("freeCashFlow", 3.0),
                    _row("payDiv", 4.0),
                ],
            )
        ],
        [],
    )
    (balance,) = bundle.balances
    assert_that(balance.non_current_assets, equal_to(-1))
    assert_that(balance.inventories, equal_to(-1))
    assert_that(balance.receivables, equal_to(-1))
    (flow,) = bundle.cashflows
    assert_that(flow.deprec, equal_to(0))


class StubTiingoClient:
    def __init__(self, statements=None, daily=None):
        self.statements = statements or []
        self.daily = daily or []
        self.statement_calls = []
        self.daily_calls = []

    def get_fundamentals_statements(self, ticker, asReported=False, **kwargs):
        self.statement_calls.append((ticker, asReported, kwargs))
        return self.statements

    def get_fundamentals_daily(self, ticker, **kwargs):
        self.daily_calls.append((ticker, kwargs))
        return self.daily


def test_source_requests_as_reported_and_bounds_daily():
    client = StubTiingoClient(
        statements=[_full_bundle()],
        daily=[{"date": "2024-04-01T00:00:00.000Z", "marketCap": 42.0}],
    )
    log = CapturingLog()
    source = TiingoFundamentalsSource(api_key="test-key", client=client, log=log)

    bundles = source.get_fundamentals(["aapl"], datetime.date(2024, 4, 30))

    assert_that(client.statement_calls[0][0], equal_to("AAPL"))
    assert_that(client.statement_calls[0][1], equal_to(True))
    assert_that(client.daily_calls[0][0], equal_to("AAPL"))
    assert_that(client.daily_calls[0][1].get("endDate"), equal_to("2024-04-30"))
    assert_that(bundles["AAPL"].incomes[0].netIncome, equal_to(29789000000.0))
    assert_that(
        log.lines,
        equal_to(["Connected to Tiingo fundamentals", "Subscribing to AAPL"]),
    )


def test_source_needs_no_symbols_logged_and_empty():
    source = TiingoFundamentalsSource(
        api_key="k", client=StubTiingoClient(), log=CapturingLog()
    )
    assert_that(source.get_fundamentals([], datetime.date(2024, 4, 30)), equal_to({}))


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv(TIINGO_API_KEY_ENV_VAR, raising=False)
    with pytest.raises(ValueError) as error:
        TiingoFundamentalsSource(log=CapturingLog())
    assert_that(str(error.value), contains_string(TIINGO_API_KEY_ENV_VAR))


def test_from_env_reads_the_key(monkeypatch):
    monkeypatch.setenv(TIINGO_API_KEY_ENV_VAR, "env-key")
    source = TiingoFundamentalsSource.from_env(
        CapturingLog(), client=StubTiingoClient()
    )
    assert_that(source.api_key, equal_to("env-key"))
    assert_that(os.environ.get(TIINGO_API_KEY_ENV_VAR), equal_to("env-key"))
