import psycopg2

from mrmkt.common.sql import InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.ext.postgres import PostgresSqlClient

cnv = InsecureSqlGenerator()
pool = psycopg2.pool.SimpleConnectionPool(1, 20, user="postgres",
                                          password="local",
                                          host="127.0.0.1",
                                          port="5432",
                                          database="mrmkt")
sql = PostgresSqlClient(cnv, pool)
repo = SqlFinancialRepository(sql)
