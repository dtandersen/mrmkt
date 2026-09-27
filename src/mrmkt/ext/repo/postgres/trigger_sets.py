"""Postgres trigger-set repository (mixin)."""

from contextlib import suppress
from dataclasses import dataclass

from mrmkt.common.sql import Duplicate, SqlClient
from mrmkt.repo.trigger_sets import TriggerSetNotFound, TriggerSetRepository


class PostgresTriggerSetRepository(TriggerSetRepository):
    """Trigger sets over SQL; combined via PostgresBackend."""

    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def create_set(self, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("trigger set name must not be blank")
        cleaned = name.strip()
        try:
            self.sql_client.insert("trigger_set", TriggerSetRow(cleaned))
        except Duplicate as error:
            raise ValueError(f"trigger set {cleaned!r} already exists") from error
        return cleaned

    def add_to_set(self, set_name: str, trigger_name: str) -> None:
        sets = self.sql_client.select(
            "select name from trigger_set where name = %s",
            lambda row: row["name"],
            (set_name,),
        )
        if not sets:
            raise TriggerSetNotFound(set_name)
        triggers = self.sql_client.select(
            "select name from trigger where name = %s",
            lambda row: row["name"],
            (trigger_name,),
        )
        if not triggers:
            raise ValueError(f"no trigger with name {trigger_name!r}")
        with suppress(Duplicate):
            self.sql_client.insert(
                "trigger_set_member", TriggerSetMemberRow(set_name, trigger_name)
            )

    def remove_from_set(self, set_name: str, trigger_name: str) -> bool:
        return self.sql_client.delete(
            "delete from trigger_set_member where set_name = %s and trigger_name = %s",
            (set_name, trigger_name),
        )

    def list_set_members(self, set_name: str) -> list[str]:
        sets = self.sql_client.select(
            "select name from trigger_set where name = %s",
            lambda row: row["name"],
            (set_name,),
        )
        if not sets:
            raise TriggerSetNotFound(set_name)
        return self.sql_client.select(
            "select trigger_name from trigger_set_member "
            "where set_name = %s order by trigger_name asc",
            lambda row: row["trigger_name"],
            (set_name,),
        )


@dataclass
class TriggerSetRow:
    name: str


@dataclass
class TriggerSetMemberRow:
    set_name: str
    trigger_name: str
