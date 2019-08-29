import psycopg2
import logging
from financial import FinancialGateway
from finrepo import FinancialRepository, SqlFinancialRepository
from fingtwy import DefaultFmpApi, FMPFinancialGateway
from postgres import PostgresSqlClient
from sql import InsecureSqlGenerator, Duplicate


class FinancialLoader(object):
    def __init__(self, fin_gate: FinancialGateway, fin_db: FinancialRepository):
        self.fin_db = fin_db
        self.fin_gate = fin_gate

    def load(self, symbol: str):
        income_statements = self.fin_gate.income_statement(symbol)
        for i in income_statements:
            try:
                self.fin_db.add_income(i)
            except Duplicate:
                pass

        balance_sheets = self.fin_gate.balance_sheet(symbol)
        for b in balance_sheets:
            try:
                self.fin_db.add_balance_sheet(b)
            except Duplicate:
                pass

    def load_all(self):
        for symbol in self.fin_gate.get_stocks():
            self.load(symbol)


def main():
    # logging.basicConfig(level=logging.DEBUG)
    api = DefaultFmpApi()
    fin_gtwy = FMPFinancialGateway(api)
    cnv = InsecureSqlGenerator()
    pool = psycopg2.pool.SimpleConnectionPool(1, 20,user = "postgres",
                                              password = "local",
                                              host = "127.0.0.1",
                                              port = "5432",
                                              database = "mrmkt")
    sql = PostgresSqlClient(cnv, pool)
    pg = SqlFinancialRepository(sql)
    loader = FinancialLoader(fin_gtwy, pg)
    loader.load('ENPH')


if __name__ == "__main__":
    main()
