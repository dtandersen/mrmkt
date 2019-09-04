from typing import Type, List

import psycopg2

from common.sqlfinrepo import SqlFinancialRepository
from ext.fmp import FMPFinancialGateway, FmpApi
from ext.postgres import PostgresSqlClient
from apprunner.runner import App, AppRunner, Injector
from common.sql import InsecureSqlGenerator
from use_case_factory import TestMrMktUseCaseFactory, MrMktUseCaseFactory


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
    f = TestMrMktUseCaseFactory(fin_gtwy, pg)
    injector = UseCaseFactoryInjector(f)
    return injector


def bootstrap(app: Type[App], args: List[str]):
    runner = AppRunner(prod_injector())
    runner.run(app, args)


class UseCaseFactoryInjector(Injector):
    def __init__(self, command_factory: MrMktUseCaseFactory):
        self.commandFactory = command_factory

    def inject(self, obj):
        obj.use_case_factory = self.commandFactory
