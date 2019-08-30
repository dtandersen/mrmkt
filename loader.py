import logging

import psycopg2
import sys
from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Type

from financial import FinancialGateway
from fingtwy import FMPFinancialGateway, DefaultFmpApi
from finrepo import FinancialRepository, SqlFinancialRepository
from postgres import PostgresSqlClient
from runner import App, AppRunner, Injector
from sql import Duplicate, InsecureSqlGenerator


@dataclass
class FinancialLoaderRequest:
    symbol: str


class FinancialLoaderResult:
    def on_load_symbol(self, symbol: str):
        pass


class FinancialLoader(object):
    result: FinancialLoaderResult

    def __init__(self, fin_gate: FinancialGateway, fin_db: FinancialRepository):
        self.fin_db = fin_db
        self.fin_gate = fin_gate

    def run(self, request: FinancialLoaderRequest, result: FinancialLoaderResult):
        self.result = result
        if request.symbol is not None:
            self.load(request.symbol)
        else:
            self.load_all()

    def load(self, symbol: str):
        self.result.on_load_symbol(symbol)
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


class MrMktCommandFactory:
    @abstractmethod
    def loader(self) -> FinancialLoader:
        pass


@dataclass
class TestMrMktCommandFactory(MrMktCommandFactory):
    fingate: FinancialGateway
    findb: FinancialRepository

    def loader(self):
        return FinancialLoader(self.fingate, self.findb)


class CommandFactoryInjector(Injector):
    def __init__(self, command_factory: MrMktCommandFactory):
        self.commandFactory = command_factory

    def inject(self, obj):
        obj.commandFactory = self.commandFactory


class LoaderMain(App):
    commandFactory: MrMktCommandFactory

    def run(self, args: List[str]):
        loader = self.commandFactory.loader()
        result = FinancialLoaderResult()
        result.on_load_symbol = self.print_symbol
        if len(args) > 0:
            symbol = args[0]
        else:
            symbol = None
        loader.run(FinancialLoaderRequest(symbol=symbol), result)

    @staticmethod
    def print_symbol(symbol: str):
        print(f"Fetching {symbol}...")


def prod_injector() -> Injector:
    api = DefaultFmpApi()
    fin_gtwy = FMPFinancialGateway(api)
    cnv = InsecureSqlGenerator()
    pool = psycopg2.pool.SimpleConnectionPool(1, 20, user="postgres",
                                              password="local",
                                              host="127.0.0.1",
                                              port="5432",
                                              database="mrmkt")
    sql = PostgresSqlClient(cnv, pool)
    pg = SqlFinancialRepository(sql)
    f = TestMrMktCommandFactory(fin_gtwy, pg)
    injector = CommandFactoryInjector(f)
    return injector


def bootstrap(app: Type[App], args: List[str]):
    runner = AppRunner(prod_injector())
    runner.run(app, args)


def main():
    # logging.basicConfig(level=logging.DEBUG)
    bootstrap(LoaderMain, sys.argv[1:])


if __name__ == "__main__":
    main()
