import sys
from typing import List

from bootstrapper import bootstrap
from mrmkt.apprunner.runner import App
from mrmkt.usecase.price_loader import PriceLoaderRequest, PriceLoaderResult
from use_case_factory import MrMktUseCaseFactory


class FetchPricesApp(App):
    use_case_factory: MrMktUseCaseFactory

    def run(self, args: List[str]):
        request = PriceLoaderRequest()
        result = PriceLoaderResult(lookup=self.print_symbol)

        if len(args) > 0:
          request.tickers = args

        usecase = self.use_case_factory.fetch_prices()
        usecase.execute(request, result)

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
