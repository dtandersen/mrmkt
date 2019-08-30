from typing import Type, List

import psycopg2

from ext.fmp import FMPFinancialGateway, FmpApi
from common.finrepo import SqlFinancialRepository
from ext.postgres import PostgresSqlClient
from apprunner.runner import App, AppRunner, Injector
from common.sql import InsecureSqlGenerator
from command_factory import TestMrMktCommandFactory, MrMktCommandFactory


def prod_injector() -> Injector:
    api = FmpApi()
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