import io
import textwrap
import unittest
from contextlib import redirect_stdout
from typing import List

from bootstrapper import UseCaseFactoryInjector
from fetch import FetchFinancialsApp
from mrmkt.apprunner.runner import AppRunner
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.common.testfinrepo import FinancialTestRepository
from use_case_factory import TestMrMktUseCaseFactory


class TestFetchApp(unittest.TestCase):
    def setUp(self):
        self.sourcerepo = FinancialTestRepository()

    def test_fetch_apple(self):
        self.execute(['AAPL'])

        self.thenConsoleIs('''\
                           Fetching AAPL...
                           ''')

    def test_fetch_nvidia_and_google(self):
        self.given_google_financials()
        self.given_nvidia_financials()

        self.execute()

        self.thenConsoleIs('''\
                           Fetching GOOG...
                           Fetching NVDA...
                           ''')

    def execute(self, args: List[str] = None):
        if args is None:
            args = []

        injector = UseCaseFactoryInjector(TestMrMktUseCaseFactory(
            fingate=self.sourcerepo,
            findb=InMemoryFinancialRepository()))
        runner = AppRunner(injector)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.run(FetchFinancialsApp, args)

        self.console = stdout.getvalue()

    def given_nvidia_financials(self):
        self.sourcerepo.add_nvidia_financials()

    def given_google_financials(self):
        self.sourcerepo.add_google_financials()

    def thenConsoleIs(self, expected: str):
        self.assertEqual(self.console, textwrap.dedent(expected))
