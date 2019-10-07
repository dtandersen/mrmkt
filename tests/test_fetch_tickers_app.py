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
from tests.testenv import TestEnvironment
from use_case_factory import TestMrMktUseCaseFactory


class TestFetchApp(unittest.TestCase):
    def setUp(self):
        self.env = TestEnvironment()

    def test_fetch_apple(self):

        self.execute()

        self.thenConsoleIs('''\
                           Fetching tickers...
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

    def given_nvidia_financials(self):
        self.env.remote.add_nvidia_financials()

    def given_google_financials(self):
        self.env.remote.add_google_financials()

    def thenConsoleIs(self, expected: str):
        self.assertEqual(self.console, textwrap.dedent(expected))

    def given_apple_financials(self):
        self.env.remote.add_apple_financials()
