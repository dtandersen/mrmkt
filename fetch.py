import sys
from typing import List

from bootstrapper import bootstrap
from usecase.fetch import FinancialLoaderResult, FinancialLoaderRequest
from apprunner.runner import App
from use_case_factory import MrMktUseCaseFactory


class FetchFinancialsApp(App):
    use_case_factory: MrMktUseCaseFactory

    def run(self, args: List[str]):
        result = FinancialLoaderResult()
        result.on_load_symbol = self.print_symbol
        if len(args) > 0:
            symbol = args[0]
        else:
            symbol = None

        usecase = self.use_case_factory.fetch_financials()
        usecase.execute(FinancialLoaderRequest(symbol=symbol), result)

    @staticmethod
    def print_symbol(symbol: str):
        print(f"Fetching {symbol}...")


def main():
    bootstrap(FetchFinancialsApp, sys.argv[1:])


if __name__ == "__main__":
    main()
