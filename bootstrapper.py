from typing import Type, List

import psycopg2

from fingtwy import DefaultFmpApi, FMPFinancialGateway
from finrepo import SqlFinancialRepository
from postgres import PostgresSqlClient
from runner import App, AppRunner, Injector
from sql import InsecureSqlGenerator
from command import TestMrMktCommandFactory, MrMktCommandFactory


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


class CommandFactoryInjector(Injector):
    def __init__(self, command_factory: MrMktCommandFactory):
        self.commandFactory = command_factory

    def inject(self, obj):
        obj.commandFactory = self.commandFactory
