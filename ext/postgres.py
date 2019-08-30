import logging
import psycopg2
from psycopg2.pool import AbstractConnectionPool
from common.sql import SqlGenerator, SqlClient, Duplicate


class PostgresSqlClient(SqlClient):
    def __init__(self, converter: SqlGenerator, pool: AbstractConnectionPool):
        self.converter = converter
        self.pool = pool

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
