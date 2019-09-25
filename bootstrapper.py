from typing import Type, List

import psycopg2

from mrmkt.apprunner.runner import Injector, App, AppRunner
from mrmkt.common.sql import InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.ext.fmp import FmpClient, FMPReadOnlyFinancialRepository
from mrmkt.ext.postgres import PostgresSqlClient
from use_case_factory import TestMrMktUseCaseFactory, MrMktUseCaseFactory


def prod_injector() -> Injector:
    api = FmpClient()
    fin_gtwy = FMPReadOnlyFinancialRepository(api)
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
