import sys
from typing import List

from bootstrapper import bootstrap
from usecase.loader import FinancialLoaderResult, FinancialLoaderRequest
from apprunner.runner import App
from command_factory import MrMktCommandFactory


class LoaderApp(App):
    commandFactory: MrMktCommandFactory

    def run(self, args: List[str]):
        result = FinancialLoaderResult()
        result.on_load_symbol = self.print_symbol
        if len(args) > 0:
            symbol = args[0]
        else:
            symbol = None

        loader = self.commandFactory.loader()
        loader.run(FinancialLoaderRequest(symbol=symbol), result)

    @staticmethod
    def print_symbol(symbol: str):
        print(f"Fetching {symbol}...")


def main():
    bootstrap(LoaderApp, sys.argv[1:])


if __name__ == "__main__":
    main()
