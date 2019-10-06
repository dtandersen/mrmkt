import logging
from typing import Type, List

import psycopg2
import yaml
from tiingo import TiingoClient

from mrmkt.apprunner.runner import Injector, App, AppRunner
from mrmkt.common.clock import WallClock, Clock
from mrmkt.common.environment import MrMktEnvironment
from mrmkt.common.sql import InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.common.tiingorepo import TiingoPriceRepository
from mrmkt.ext.fmp import FmpClient, FMPReadOnlyFinancialRepository
from mrmkt.ext.postgres import PostgresSqlClient
from mrmkt.repo.provider import ReadOnlyMarketDataProvider, MarketDataProvider
from use_case_factory import TestMrMktUseCaseFactory, MrMktUseCaseFactory


class ProdEnv(MrMktEnvironment):
    def __init__(self):
        # try:
        #     import http.client as http_client
        # except ImportError:
        #     # Python 2
        #     import httplib as http_client
        # http_client.HTTPConnection.debuglevel = 1
        # logging.basicConfig(level=logging.DEBUG)
        with open('config.yaml') as f:
            # use safe_load instead load
            config = yaml.safe_load(f)
        api = FmpClient()
        fin_gtwy = FMPReadOnlyFinancialRepository(api)
        key_ = config['tiingo']['api_key']
        # print(key_)
        tconfig = {}
        tconfig["api_key"] = str(key_)
        tconfig["session"] = True
        # print(tconfig)
        tiingo_client = TiingoClient(tconfig)
        tg = TiingoPriceRepository(tiingo_client)
        dbconfig = config['database']
        pool = psycopg2.pool.SimpleConnectionPool(1, 20, user=dbconfig['user'],
                                                  password=dbconfig['password'],
                                                  host=dbconfig['host'],
                                                  port=dbconfig['port'],
                                                  database=dbconfig['database'])
        cnv = InsecureSqlGenerator()
        sql = PostgresSqlClient(cnv, pool)
        pg = SqlFinancialRepository(sql)
        self._remote = ReadOnlyMarketDataProvider(financials=fin_gtwy, prices=tg, tickers=fin_gtwy)
        self._local = MarketDataProvider(financials=pg, prices=pg, tickers=pg)
        self._clock = WallClock()

    @property
    def local(self) -> MarketDataProvider:
        return self._local

    @property
    def remote(self) -> ReadOnlyMarketDataProvider:
        return self._remote

    @property
    def clock(self) -> Clock:
        return self._clock


def prod_injector() -> Injector:
    with open('config.yaml') as f:
        # use safe_load instead load
        config = yaml.safe_load(f)

    # api = FmpClient()
    # fin_gtwy = FMPReadOnlyFinancialRepository(api)
    # cnv = InsecureSqlGenerator()
    # dbconfig = config['database']
    # pool = psycopg2.pool.SimpleConnectionPool(1, 20, dbconfig['user'],
    #                                           dbconfig['password'],
    #                                           dbconfig['host'],
    #                                           dbconfig['port'],
    #                                           dbconfig['database'])
    # sql = PostgresSqlClient(cnv, pool)
    # pg = SqlFinancialRepository(sql)
    # rorepo = ReadOnlyMarketDataProvider(financials=fin_gtwy, prices=fin_gtwy, tickers=fin_gtwy)
    # rwrepo = MarketDataProvider(financials=pg, prices=pg, tickers=pg)
    env = ProdEnv()
    f = TestMrMktUseCaseFactory(env=env)
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
