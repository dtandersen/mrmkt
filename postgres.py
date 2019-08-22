from psycopg2.pool import SimpleConnectionPool
from sql import SqlGenerator, SqlClient


class PostgresSqlClient(SqlClient):
    def __init__(self, converter: SqlGenerator, pool: SimpleConnectionPool):
        self.converter = converter
        self.pool = pool

    def insert(self, table: str, values: any):
        with self.pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute(self.converter.to_insert(table, values))
