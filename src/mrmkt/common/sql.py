import dataclasses
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import asdict
from typing import Any


@dataclasses.dataclass
class JsonField:
    data: Any


class SqlClient:
    @abstractmethod
    def insert(self, table: str, values: Any):
        pass

    @abstractmethod
    def select(
        self, query: str, mapper: Callable[[dict], object], params: tuple = ()
    ) -> list:
        pass

    @abstractmethod
    def delete(self, query: str, params: tuple = ()) -> bool:
        pass


class MockSqlClient(SqlClient):
    inserts: list[dict]
    selects: dict

    def __init__(self):
        self.queries = []
        self.inserts = []
        self.selects = {}

    def select(self, query: str, mapper: Callable[[dict], object], params: tuple = ()):
        # logging.debug("{query} => {rows}")
        rows = [mapper(row) for row in self.selects[query]]
        return rows

    def insert(self, table: str, values: Any):
        self.inserts.append({"table": table, "values": values})

    def delete(self, query: str, params: tuple = ()) -> bool:
        self.queries.append(query)
        return True

    def append_select(self, query: str, rows: list[Any]):
        self.selects[query] = [asdict(row) for row in rows]


class Duplicate(Exception):
    def __init__(self, message):
        self.message = message
