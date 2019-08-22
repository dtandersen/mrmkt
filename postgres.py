from psycopg2.pool import SimpleConnectionPool
from sql import SqlConverter, SqlClient


class PostgresSqlClient(SqlClient):
    def __init__(self, converter: SqlConverter, pool: SimpleConnectionPool):
        self.converter = converter
        self.pool = pool

    def insert(self, table: str, values: any):
        conn = self.pool.getconn()

        cur = conn.cursor()
        cur.execute(self.converter.to_insert(table, values))
        cur.close()
