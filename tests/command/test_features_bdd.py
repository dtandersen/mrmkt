"""BDD coverage for the feature commands, driven directly."""

import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.command.create_feature import CreateFeature, CreateFeatureRequest
from mrmkt.command.delete_feature import DeleteFeature, DeleteFeatureRequest
from mrmkt.command.list_features import ListFeatures, ListFeaturesRequest
from mrmkt.command.show_feature import ShowFeature, ShowFeatureRequest
from mrmkt.common.clock import ClockStub
from mrmkt.entity.feature import Feature
from mrmkt.entity.ticker import Ticker

scenarios(
    str(Path(__file__).parent.parent / "features" / "command" / "features.feature")
)


class SymbolSpecificTickerLookup:
    """Fail if create-feature regresses to scanning the whole catalog."""

    def __init__(self, repository):
        self.repository = repository

    def list_tickers_by_symbol(self, symbol):
        return self.repository.list_tickers_by_symbol(symbol)

    def get_tickers(self):
        raise AssertionError("feature create must use a symbol-specific listing lookup")


@pytest.fixture
def feature_context(financial_repository):
    clock = ClockStub()
    clock.set_time(datetime.date(2026, 9, 27))
    ticker_lookup = SymbolSpecificTickerLookup(financial_repository)
    return SimpleNamespace(
        clock=clock,
        result=None,
        removed=0,
        create=CreateFeature(financial_repository, ticker_lookup, clock),
        delete=DeleteFeature(financial_repository),
        list=ListFeatures(financial_repository),
        show=ShowFeature(financial_repository),
    )


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the ticker catalog contains:")
def seed_tickers(feature_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse('the fake clock says today is "{today}"'))
def set_clock(feature_context, today):
    feature_context.clock.set_time(datetime.date.fromisoformat(today))


@given("stored features:")
def seed_features(feature_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        raw = row["value"]
        try:
            num: float | None = float(raw)
            text: str | None = None
        except ValueError:
            num, text = None, raw
        financial_repository.add_feature(
            Feature(
                symbol=row["symbol"],
                exchange=row["exchange"],
                feature=row["feature"],
                date=datetime.date.fromisoformat(row["date"]),
                value_num=num,
                value_text=text,
            )
        )


def _render(row):
    value = (
        f"{row.value_num:g}" if row.value_num is not None else (row.value_text or "")
    )
    return f"{row.symbol} | {row.date.isoformat()} | {row.feature} | {value}"


@when(parsers.parse('I create feature "{assignment}" for "{symbol}" on "{day}"'))
def create_dated(feature_context, assignment, symbol, day):
    feature_context.result = feature_context.create.execute(
        CreateFeatureRequest(symbol=symbol, assignment=assignment, date=day)
    )


@when(parsers.parse('I create feature "{assignment}" for "{symbol}" with no date'))
def create_undated(feature_context, assignment, symbol):
    feature_context.result = feature_context.create.execute(
        CreateFeatureRequest(symbol=symbol, assignment=assignment, date=None)
    )


@when(parsers.parse('I show feature "{name}" for "{symbol}"'))
def show(feature_context, name, symbol):
    feature_context.result = feature_context.show.execute(
        ShowFeatureRequest(symbol=symbol, name=name)
    )


@when(parsers.parse('I list features for "{symbol}"'))
def list_rows(feature_context, symbol):
    feature_context.result = feature_context.list.execute(
        ListFeaturesRequest(symbol=symbol)
    )


@when(parsers.parse('I delete feature "{name}" for "{symbol}"'))
def delete(feature_context, name, symbol):
    result = feature_context.delete.execute(
        DeleteFeatureRequest(symbol=symbol, name=name)
    )
    feature_context.result = result
    feature_context.removed = result.result if result.is_success() else 0


@then(parsers.parse('showing feature "{name}" for "{symbol}" reports not found'))
def reshow_missing(feature_context, name, symbol):
    feature_context.result = feature_context.show.execute(
        ShowFeatureRequest(symbol=symbol, name=name)
    )
    assert_that(feature_context.result.is_not_found(), equal_to(True))


@then("the command succeeds")
def succeeds(feature_context):
    assert_that(feature_context.result.is_success(), equal_to(True))


@then("the command fails with invalid data")
def invalid(feature_context):
    assert_that(feature_context.result.is_invalid_data(), equal_to(True))


@then("the command reports not found")
def not_found(feature_context):
    assert_that(feature_context.result.is_not_found(), equal_to(True))


@then(parsers.parse('the stored feature reads back as "{line}"'))
def stored_reads_back(feature_context, line):
    assert_that(_render(feature_context.result.result), equal_to(line))


@then(parsers.parse('the shown feature reads back as "{line}"'))
def shown_reads_back(feature_context, line):
    assert_that(_render(feature_context.result.result), equal_to(line))


@then("the feature list reads back as:")
def list_reads_back(feature_context, datatable):
    expected = [row[0] for row in datatable[1:]]
    assert_that(
        [_render(row) for row in feature_context.result.result], equal_to(expected)
    )


@then(parsers.parse("{count:d} rows were removed"))
def removed_count(feature_context, count):
    assert_that(feature_context.removed, equal_to(count))
