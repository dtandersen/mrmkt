import inspect
import textwrap
import unittest
import io

from contextlib import redirect_stdout
from typing import List

from bootstrapper import UseCaseFactoryInjector
from common.finrepo import InMemoryFinancialRepository
from common.testfingate import TestFinancialGateway
from fetch import FetchFinancialsApp
from apprunner.runner import AppRunner
from use_case_factory import TestMrMktUseCaseFactory


class TestLoad(unittest.TestCase):
    def setUp(self):
        self.fingate = TestFinancialGateway()

    def test_fetch_apple(self):
        self.execute(['AAPL'])

        self.thenConsoleIs('''\
                           Fetching AAPL...
                           ''')

    def test_fetch_nvidia_and_google(self):
        self.givenGoogleFinancials()
        self.givenNvidiaFinancials()

        self.execute()

        self.thenConsoleIs('''\
                           Fetching GOOG...
                           Fetching NVDA...
                           ''')

    def givenNvidiaFinancials(self):
        self.fingate.add_nvidia_financials()

    def givenGoogleFinancials(self):
        self.fingate.add_google_financials()

    def execute(self, args: List[str] = None):
        if args is None:
            args = []

        injector = UseCaseFactoryInjector(TestMrMktUseCaseFactory(
            fingate=self.fingate,
            findb=InMemoryFinancialRepository()))
        runner = AppRunner(injector)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.run(FetchFinancialsApp, args)

        self.console = stdout.getvalue()

    def thenConsoleIs(self, expected: str):
        self.assertEqual(self.console, textwrap.dedent(expected))
