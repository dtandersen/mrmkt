import sys
from typing import List

from bootstrapper import bootstrap
from mrmkt.apprunner.runner import App
from mrmkt.usecase.price_loader import PriceLoaderRequest, PriceLoaderResult
from use_case_factory import MrMktUseCaseFactory


class FetchTickersApp(App):
    use_case_factory: MrMktUseCaseFactory

    def run(self, args: List[str]):
        # request = PriceLoaderRequest()
        # result = PriceLoaderResult(lookup=self.print_symbol)
        #
        # if len(args) > 0:
        #   request.tickers = args
        print("Fetching tickers...")
        usecase = self.use_case_factory.fetch_tickers()
        usecase.execute()

    @staticmethod
    def print_symbol(data: dict):
        symbol = data['ticker']
        date = data["start"]
        end = data["end"]
        print(f"Fetching {symbol}: {date} -> {end}")


def main():
    # logging.basicConfig(level=logging.DEBUG)
    bootstrap(FetchTickersApp, sys.argv[1:])


if __name__ == "__main__":
    main()
# import csv
# from dataclasses import dataclass
#
# import psycopg2
#
# from mrmkt.common.sql import InsecureSqlGenerator, Duplicate
# from mrmkt.ext.postgres import PostgresSqlClient
#
#
# @dataclass
# class TickerRow:
#     ticker: str
#     exchange: str
#     type: str
#
#
# cnv = InsecureSqlGenerator()
# pool = psycopg2.pool.SimpleConnectionPool(1, 20, user="postgres",
#                                           password="local",
#                                           host="127.0.0.1",
#                                           port="5432",
#                                           database="mrmkt")
# sql = PostgresSqlClient(cnv, pool)
#
# with open('C:\\Users\\David\\Downloads\\supported_tickers\\supported_tickers2.csv') as csvfile:
#     readCSV = csv.reader(csvfile, delimiter=',')
#     for row in readCSV:
#         x = TickerRow(ticker=row[0], exchange=row[1], type=row[2])
#         try:
#             sql.insert("ticker", x)
#         except Duplicate:
#             pass
