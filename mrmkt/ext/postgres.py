import logging
from typing import Callable

import psycopg2
import psycopg2.extras
from psycopg2.pool import AbstractConnectionPool

from mrmkt.common.sql import SqlClient, SqlGenerator, Duplicate, InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository


class PostgresSqlClient(SqlClient):
    def __init__(self, converter: SqlGenerator, pool: AbstractConnectionPool):
        self.converter = converter
        self.pool = pool

    def select(self, query: str, mapper: Callable[[dict], object]):
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    sql = query
                    cur.execute(sql)
                    rows = cur.fetchall()
                    # rows = list(map(lambda x: x[0], cur.description))
                    logging.debug(f"{sql} => {rows}")
                    # x = [mapper(row) for row in rows]
                    # logging.debug(f"{sql} => {x}")
                    # z= psycopg2.RealDictRow()
                    r2 = [mapper(dict(row)) for row in rows]
                    # logging.debug(f"{sql} => {r2}")
                    return r2
        finally:
            self.pool.putconn(conn)

    def insert(self, table: str, values: any):
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    sql = self.converter.to_insert(table, values)
                    logging.debug(sql)
                    try:
                        cur.execute(sql)
                    except psycopg2.errors.UniqueViolation as err:
                        raise Duplicate(err)
        finally:
            self.pool.putconn(conn)

    def delete(self, query: str):
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    sql = query
                    cur.execute(sql)
        finally:
            self.pool.putconn(conn)


def postgresx() -> SqlFinancialRepository:
    cnv = InsecureSqlGenerator()
    pool = psycopg2.pool.SimpleConnectionPool(1, 20, user="postgres",
                                              password="local",
                                              host="127.0.0.1",
                                              port="5432",
                                              database="mrmkt")
    sql = PostgresSqlClient(cnv, pool)
    repo = SqlFinancialRepository(sql)
    return repo
