import unittest
import io

from contextlib import redirect_stdout

from bootstrapper import CommandFactoryInjector
from financial import TestFinancialGateway
from finrepo import InMemoryFinancialRepository
from loader_app import LoaderApp
from runner import AppRunner
from command import TestMrMktCommandFactory


class TestLoad(unittest.TestCase):
    def test_appl(self):
        fingate = TestFinancialGateway()
        injector = CommandFactoryInjector(TestMrMktCommandFactory(fingate=fingate, findb=InMemoryFinancialRepository()))
        runner = AppRunner(injector)

        f = io.StringIO()
        with redirect_stdout(f):
            runner.run(LoaderApp, ['AAPL'])

        self.assertEqual("Fetching AAPL...\n", f.getvalue())

    def test_nvda_goog(self):
        fingate = TestFinancialGateway()
        fingate.addGoogleFinancials()
        fingate.addNvidiaFinancials()
        injector = CommandFactoryInjector(TestMrMktCommandFactory(fingate=fingate, findb=InMemoryFinancialRepository()))
        runner = AppRunner(injector)

        f = io.StringIO()
        with redirect_stdout(f):
            runner.run(LoaderApp, [])

        self.assertEqual("Fetching GOOG...\n" +
                         "Fetching NVDA...\n",
                         f.getvalue())
