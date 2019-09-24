import logging
import sys
from typing import List

from bootstrapper import bootstrap
from usecase.fetch import FinancialLoaderResult, FinancialLoaderRequest
from apprunner.runner import App
from use_case_factory import MrMktUseCaseFactory
from usecase.price_loader import PriceLoaderResult, PriceLoaderRequest


class FetchPricesApp(App):
    use_case_factory: MrMktUseCaseFactory

    def run(self, args: List[str]):
        result = PriceLoaderResult(lookup=self.print_symbol)
        # result.on_load_symbol = self.print_symbol
        # if len(args) > 0:
        #     symbol = args[0]
        # else:
        #     symbol = None
        #
        usecase = self.use_case_factory.fetch_prices()
        usecase.execute(PriceLoaderRequest(), result)

    @staticmethod
    def print_symbol(data: dict):
        symbol = data['ticker']
        date = data["start"]
        print(f"Fetching {symbol} => {date}...")


def main():
    # logging.basicConfig(level=logging.DEBUG)
    bootstrap(FetchPricesApp, sys.argv[1:])


if __name__ == "__main__":
    main()
