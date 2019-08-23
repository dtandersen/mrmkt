import psycopg2
import logging
from financial import FinancialGateway
from findb import FinancialRepository, SqlFinancialRepository
from fmp import DefaultFmpApi, FMPFinancialGateway
from postgres import PostgresSqlClient
from sql import InsecureSqlGenerator


class StockLoader(object):
    def __init__(self, fin_gate: FinancialGateway, fin_db: FinancialRepository):
        self.fin_db = fin_db
        self.fin_gate = fin_gate

    def load_all(self):
        for symbol in self.fin_gate.get_stocks():
            income_statement = self.fin_gate.income_statement(symbol)
            if income_statement:
                self.fin_db.add_income(income_statement)

            balance_sheet = self.fin_gate.balance_sheet(symbol)
            if balance_sheet:
                self.fin_db.add_balance_sheet(balance_sheet)


def main():
    logging.basicConfig(level=logging.DEBUG)
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
    loader = StockLoader(fin_gtwy, pg)
    loader.load_all()


if __name__ == "__main__":
    main()
