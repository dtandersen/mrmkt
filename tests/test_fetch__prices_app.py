import io
import textwrap
import unittest
from contextlib import redirect_stdout
from typing import List

from bootstrapper import UseCaseFactoryInjector
from fetch_prices import FetchPricesApp
from mrmkt.apprunner.runner import AppRunner
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.common.testfinrepo import FinancialTestRepository
from mrmkt.repo.provider import ReadOnlyMarketDataProvider, MarketDataProvider
from use_case_factory import TestMrMktUseCaseFactory


class TestFetchApp(unittest.TestCase):
    def setUp(self):
        self.sourcerepo = FinancialTestRepository()

    def test_fetch_apple(self):
        self.given_apple_financials()

        self.execute(['AAPL'])

        self.thenConsoleIs('''\
                           Fetching AAPL => None...
                           ''')

    def test_fetch_nvidia_and_google(self):
        self.given_google_financials()
        self.given_nvidia_financials()

        self.execute()

        self.thenConsoleIs('''\
                           Fetching GOOG => None...
                           Fetching NVDA => None...
                           ''')

    def test_fetch_nvidia_and_google2(self):
        self.given_apple_financials()
        self.given_google_financials()
        self.given_nvidia_financials()

        self.execute(["GOOG", "NVDA"])

        self.thenConsoleIs('''\
                           Fetching GOOG => None...
                           Fetching NVDA => None...
                           ''')

    def execute(self, args: List[str] = None):
        if args is None:
            args = []

        destrepo = InMemoryFinancialRepository()
        all = ReadOnlyMarketDataProvider(financials=self.sourcerepo, prices=self.sourcerepo, tickers=self.sourcerepo)
        allw = MarketDataProvider(financials=destrepo, prices=destrepo, tickers=destrepo)
        injector = UseCaseFactoryInjector(TestMrMktUseCaseFactory(
            fingate2=all,
            findb2=allw))
        runner = AppRunner(injector)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.run(FetchPricesApp, args)

        self.console = stdout.getvalue()

    def given_nvidia_financials(self):
        self.sourcerepo.add_nvidia_financials()

    def given_google_financials(self):
        self.sourcerepo.add_google_financials()

    def thenConsoleIs(self, expected: str):
        self.assertEqual(self.console, textwrap.dedent(expected))

    def given_apple_financials(self):
        self.sourcerepo.add_apple_financials()
