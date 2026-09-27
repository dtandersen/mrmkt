"""Postgres trigger repository (mixin)."""

import datetime
from dataclasses import dataclass

from mrmkt.common.sql import Duplicate, SqlClient
from mrmkt.entity.trigger import (
    FREQUENCIES,
    OPERATORS,
    Trigger,
    normalize_trigger_indicator,
)
from mrmkt.repo.triggers import TriggerRepository


class PostgresTriggerRepository(TriggerRepository):
    """Stored triggers over SQL; combined via PostgresBackend."""

    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def list_triggers(self, enabled_only: bool = False) -> list[Trigger]:
        query = "select * from trigger order by id asc"
        if enabled_only:
            query = "select * from trigger where enabled = %s order by id asc"
            return self.sql_client.select(query, self.trigger_mapper, (True,))
        return self.sql_client.select(query, self.trigger_mapper)

    def trigger_mapper(self, row) -> Trigger:
        # DB column was renamed signal -> indicator in migration13;
        # accept both for rolling upgrades.
        return Trigger(
            id=row["id"],
            name=row["name"],
            symbol=row["symbol"],
            indicator=row.get("indicator", row.get("signal")),
            operator=row["operator"],
            value=row["value"],
            frequency=row["frequency"],
            expires_at=row["expires_at"],
            message=row["message"],
            enabled=row["enabled"],
        )

    def add_trigger(self, trigger: Trigger) -> Trigger:
        self._validate_trigger(trigger)
        if not trigger.name or not trigger.name.strip():
            raise ValueError("trigger name must not be blank")
        row = TriggerRow(
            name=trigger.name.strip(),
            symbol=trigger.symbol,
            indicator=trigger.indicator,
            operator=trigger.operator,
            value=trigger.value,
            frequency=trigger.frequency,
            expires_at=trigger.expires_at,
            message=trigger.message,
            enabled=trigger.enabled,
        )
        try:
            self.sql_client.insert("trigger", row)
        except Duplicate as error:
            raise ValueError(
                f"trigger already exists for {trigger.symbol} {trigger.indicator} {trigger.operator}"
            ) from error
        rows = self.sql_client.select(
            "select * from trigger where symbol = %s and indicator = %s and operator = %s",
            self.trigger_mapper,
            (trigger.symbol, trigger.indicator, trigger.operator),
        )
        return rows[0]

    def remove_trigger(self, trigger_id: int) -> bool:
        return self.sql_client.delete(
            "delete from trigger where id = %s",
            (trigger_id,),
        )

    def set_trigger_enabled(self, trigger_id: int, enabled: bool) -> bool:
        rows = self.sql_client.select(
            "select * from trigger where id = %s",
            self.trigger_mapper,
            (trigger_id,),
        )
        if not rows:
            return False
        current = rows[0]
        self.sql_client.delete(
            "delete from trigger where id = %s",
            (trigger_id,),
        )
        updated = TriggerRow(
            name=current.name,
            symbol=current.symbol,
            indicator=current.indicator,
            operator=current.operator,
            value=current.value,
            frequency=current.frequency,
            expires_at=current.expires_at,
            message=current.message,
            enabled=enabled,
        )
        self.sql_client.insert("trigger", updated)
        return True

    @staticmethod
    def _validate_trigger(trigger: Trigger) -> None:
        if trigger.operator not in OPERATORS:
            raise ValueError(f"{trigger.operator!r} is an invalid operator")
        if trigger.frequency not in FREQUENCIES:
            raise ValueError(f"{trigger.frequency!r} is an invalid frequency")
        normalize_trigger_indicator(trigger.indicator)


@dataclass
class TriggerRow:
    name: str
    symbol: str
    indicator: str
    operator: str
    value: float | None
    frequency: str
    expires_at: datetime.date | None
    message: str
    enabled: bool
