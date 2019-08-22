import dataclasses
from dataclasses import asdict
from typing import List


class SqlClient:
    def insert(self, table: str, values: any):
        pass


class MockSqlClient(SqlClient):
    inserts: List[dict] = []

    def insert(self, table: str, values: any):
        self.inserts.append({"table": table, "values": values})


class SqlGenerator:
    def to_insert(self, table: str, params: any) -> str:
        pass


class InsecureSqlGenerator:
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
        else:
            return f"'{value}'"
