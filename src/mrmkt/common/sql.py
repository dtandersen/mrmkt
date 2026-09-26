import dataclasses
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, cast

from mrmkt.common.util import EnhancedJSONEncoder


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


class SqlGenerator(ABC):
    @abstractmethod
    def to_insert(self, table: str, params: Any) -> tuple[str, tuple]:
        """Build a parameterized insert; implemented by gateways."""


# @author little bobby tables
class InsecureSqlGenerator(SqlGenerator):
    def to_insert(self, table: str, params: Any):
        if dataclasses.is_dataclass(params) and not isinstance(params, type):
            d = asdict(cast(Any, params))
        else:
            d = cast(dict[str, Any], params)

        keys = d.keys()
        columns = ", ".join(keys)
        values = ", ".join("%s" for _ in keys)
        query = f"insert into {table} ({columns}) values ({values})"
        # print(d.values())
        v = [self.map_obj(x) for x in d.values()]
        return query, tuple(v)

    def map_obj(self, x):
        # print(x)
        if isinstance(x, dict):
            j = json.dumps(x["data"], cls=EnhancedJSONEncoder)
            # print("json=" + j)
            return j
        else:
            return x


class Duplicate(Exception):
    def __init__(self, message):
        self.message = message
