"""Postgres feature repository (mixin)."""

import datetime
from dataclasses import dataclass

from mrmkt.common.sql import SqlClient
from mrmkt.entity.feature import Feature
from mrmkt.repo.features import FeatureRepository


class PostgresFeatureRepository(FeatureRepository):
    """Computed features over SQL; combined via PostgresBackend."""

    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def add_feature(self, feature: Feature):
        row = FeatureRow(
            symbol=feature.symbol,
            exchange=feature.exchange,
            feature=feature.feature,
            date=feature.date,
            value_num=feature.value_num,
            value_text=feature.value_text,
            computed_at=feature.computed_at,
        )
        self.sql_client.insert("feature", row)

    def delete_features(self, symbol: str, feature: str) -> int:
        doomed = self.list_features(symbol, feature)
        if doomed:
            self.sql_client.delete(
                "delete from feature where symbol = %s and feature = %s",
                (symbol, feature),
            )
        return len(doomed)

    def list_features(
        self,
        symbol: str,
        feature: str | None = None,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[Feature]:
        feature_sql = ""
        start_sql = ""
        end_sql = ""
        params: list = [symbol]
        if feature is not None:
            feature_sql = "and feature = %s "
            params.append(feature)
        if start is not None:
            start_sql = "and date >= %s "
            params.append(start.strftime("%Y-%m-%d"))
        if end is not None:
            end_sql = "and date <= %s "
            params.append(end.strftime("%Y-%m-%d"))
        rows = self.sql_client.select(
            "select * "
            + "from feature "
            + "where symbol = %s "
            + feature_sql
            + start_sql
            + end_sql
            + "order by feature asc, date asc",
            self.feature_mapper,
            tuple(params),
        )
        return rows

    def feature_mapper(self, row):
        return Feature(
            symbol=row["symbol"],
            exchange=row["exchange"],
            feature=row["feature"],
            date=row["date"],
            value_num=row["value_num"],
            value_text=row["value_text"],
            computed_at=row["computed_at"],
        )


@dataclass
class FeatureRow:
    symbol: str
    exchange: str
    feature: str
    date: datetime.date
    value_num: float | None
    value_text: str | None
    computed_at: datetime.datetime | None
