import logging
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from sql import SqlGenerator, SqlClient, Duplicate


class PostgresSqlClient(SqlClient):
    def __init__(self, converter: SqlGenerator, pool: SimpleConnectionPool):
        self.converter = converter
        self.pool = pool

    def insert(self, table: str, values: any):
        conn = None
        cur = None
        try:
            conn = self.pool.getconn()
            cur = conn.cursor()
            sql = self.converter.to_insert(table, values)
            logging.debug(sql)
            try:
                cur.execute(sql)
            except psycopg2.errors.UniqueViolation as err:
                raise Duplicate(err)
        finally:
            if conn is not None:
                self.pool.putconn(conn)
            # if cur is not None:
            #     cur.close()
