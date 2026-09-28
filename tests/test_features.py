"""Feature store tests (in-memory backend, no DB)."""

from datetime import date, datetime

import pytest

from mrmkt.common.sql import Duplicate
from mrmkt.entity.feature import Feature


def _feature(
    symbol="SPY",
    feature="rr15.low",
    day="2026-09-24",
    num: float | None = 760.42,
):
    return Feature(
        symbol=symbol,
        exchange="NASDAQ",
        feature=feature,
        date=date.fromisoformat(day),
        value_num=num,
        computed_at=datetime(2026, 9, 28, 12, 0),
    )


def test_add_and_list_round_trip(financial_repository):
    financial_repository.add_feature(_feature())
    rows = financial_repository.list_features("SPY")
    assert [(row.feature, row.value_num) for row in rows] == [("rr15.low", 760.42)]


def test_list_filters_by_feature_and_date(financial_repository):
    financial_repository.add_feature(_feature(feature="rr15.low", day="2026-09-23"))
    financial_repository.add_feature(_feature(feature="rr15.low", day="2026-09-24"))
    financial_repository.add_feature(_feature(feature="rr15.high", day="2026-09-24"))
    rows = financial_repository.list_features(
        "SPY", feature="rr15.low", start=date(2026, 9, 24)
    )
    assert [(row.feature, row.date.isoformat()) for row in rows] == [
        ("rr15.low", "2026-09-24")
    ]


def test_duplicate_key_rejected(financial_repository):
    financial_repository.add_feature(_feature())
    with pytest.raises(Duplicate):
        financial_repository.add_feature(_feature())


def test_text_valued_features(financial_repository):
    row = _feature(feature="trend.state", num=None)
    row.value_text = "up"
    financial_repository.add_feature(row)
    assert financial_repository.list_features("SPY")[0].value_text == "up"
