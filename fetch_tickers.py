import csv
from dataclasses import dataclass

import psycopg2

from mrmkt.common.sql import InsecureSqlGenerator, Duplicate
from mrmkt.ext.postgres import PostgresSqlClient


@dataclass
class TickerRow:
    ticker: str
    exchange: str
    type: str


cnv = InsecureSqlGenerator()
pool = psycopg2.pool.SimpleConnectionPool(1, 20, user="postgres",
                                          password="local",
                                          host="127.0.0.1",
                                          port="5432",
                                          database="mrmkt")
sql = PostgresSqlClient(cnv, pool)

with open('C:\\Users\\David\\Downloads\\supported_tickers\\supported_tickers2.csv') as csvfile:
    readCSV = csv.reader(csvfile, delimiter=',')
    for row in readCSV:
        x = TickerRow(ticker=row[0], exchange=row[1], type=row[2])
        try:
            sql.insert("ticker", x)
        except Duplicate:
            pass
