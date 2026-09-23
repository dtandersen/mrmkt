import dataclasses
import json
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Callable

from mrmkt.common.util import EnhancedJSONEncoder


@dataclasses.dataclass
class JsonField:
    data: any


class SqlClient:
    @abstractmethod
    def insert(self, table: str, values: any):
        pass

    @abstractmethod
    def select(self, query: str, mapper: Callable[[dict], object]) -> list:
        pass

    @abstractmethod
    def delete(self, query: str):
        pass

    @abstractmethod
    def delete2(self, query: str, params: tuple) -> bool:
        pass

    @abstractmethod
    def insert2(self, table: str, params):
        pass


class MockSqlClient(SqlClient):
    inserts: List[dict]
    selects: dict

    def __init__(self):
        self.inserts2 = []
        self.queries = []
        self.delete2_calls = []
        self.inserts = []
        self.selects = {}

    def select(self, query: str, mapper: Callable[[dict], object]):
        # logging.debug("{query} => {rows}")
        rows = [mapper(row) for row in self.selects[query]]
        return rows

    def insert(self, table: str, values: any):
        self.inserts.append({"table": table, "values": values})

    def delete(self, query: str):
        self.queries.append(query)

    def delete2(self, query: str, params: tuple) -> bool:
        self.delete2_calls.append({"query": query, "params": params})
        return False

    def append_select(self, query: str, rows: list):
        self.selects[query] = [asdict(row) for row in rows]

    def insert2(self, table: str, params):
        self.inserts2.append({"table": table, "values": params})


class SqlGenerator:
    def to_insert(self, table: str, params: any) -> str:
        pass

    def to_insert2(self, table: str, params: any) -> tuple[str, tuple]:
        pass


# @author little bobby tables
class InsecureSqlGenerator(SqlGenerator):
    def to_insert(self, table: str, params: any) -> str:
        if dataclasses.is_dataclass(params):
            d = asdict(params)
        else:
            d = params

        keys = d.keys()
        columns = ", ".join(keys)
        values = ", ".join(list(map(lambda k: InsecureSqlGenerator.to_value(d[k]), keys)))
        query = f"insert into {table} ({columns}) values ({values})"

        return query

    @staticmethod
    def to_value(value: any):
        if str.isdigit(str(value)):
            return str(value)
        elif isinstance(value, float):
            return str(value)
        else:
            return f"'{value}'"

    def to_insert2(self, table: str, params: any):
        if dataclasses.is_dataclass(params):
            d = asdict(params)
        else:
            d = params

        keys = d.keys()
        columns = ", ".join(keys)
        values = ", ".join(list(map(lambda x: "%s", keys)))
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
