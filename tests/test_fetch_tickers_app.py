import io
import textwrap
import unittest
from contextlib import redirect_stdout
from typing import List

from bootstrapper import UseCaseFactoryInjector
from fetch_prices import FetchPricesApp
from fetch_tickers import FetchTickersApp
from mrmkt.apprunner.runner import AppRunner
from mrmkt.common.util import to_date
from mrmkt.entity.ticker import Ticker
from tests.testenv import TestEnvironment
from use_case_factory import TestMrMktUseCaseFactory


class TestFetchTickersApp(unittest.TestCase):
    def setUp(self):
        self.env = TestEnvironment()

    def test_fetch_apple(self):
        self.add_remote_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))

        self.execute()

        self.thenConsoleIs('''\
                           Fetching tickers...
                           Fetched 1 tickers
                           ''')

    def execute(self, args: List[str] = None):
        if args is None:
            args = []

        injector = UseCaseFactoryInjector(TestMrMktUseCaseFactory(env=self.env))
        runner = AppRunner(injector)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.run(FetchTickersApp, args)

        self.console = stdout.getvalue()

    def add_remote_ticker(self, ticker: Ticker):
        self.env.remote.tickers.add_ticker(ticker)

    def thenConsoleIs(self, expected: str):
        self.assertEqual(self.console, textwrap.dedent(expected))
