import unittest
import io
from dataclasses import dataclass
from typing import List, Type

import loader
from contextlib import redirect_stdout

from financial import TestFinancialGateway, FinancialGateway
from finrepo import InMemoryFinancialRepository, FinancialRepository
from runner import AppRunner


@dataclass
class TestCommandFactory(loader.CommandFactory):
    fingate: FinancialGateway
    findb: FinancialRepository

    def loader(self):
        return loader.FinancialLoader(self.fingate, self.findb)


class TestLoad(unittest.TestCase):
    def test_appl(self):
        fingate = TestFinancialGateway()
        injector = loader.MyInjector(TestCommandFactory(fingate=fingate, findb=InMemoryFinancialRepository()))
        runner = AppRunner(injector)

        f = io.StringIO()
        with redirect_stdout(f):
            runner.run(loader.LoaderMain, ['AAPL'])

        self.assertEqual("Fetching AAPL...\n", f.getvalue())

    def test_nvda_goog(self):
        fingate = TestFinancialGateway()
        fingate.addGoogleFinancials()
        fingate.addNvidiaFinancials()
        injector = loader.MyInjector(TestCommandFactory(fingate=fingate, findb=InMemoryFinancialRepository()))
        runner = AppRunner(injector)

        f = io.StringIO()
        with redirect_stdout(f):
            runner.run(loader.LoaderMain, [])

        self.assertEqual("Fetching GOOG...\n" +
                         "Fetching NVDA...\n",
                         f.getvalue())
