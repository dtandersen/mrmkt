import sys
from typing import List

from bootstrapper import bootstrap
from mrmkt.apprunner.runner import App
from use_case_factory import MrMktUseCaseFactory


class FetchTickersApp(App):
    use_case_factory: MrMktUseCaseFactory

    def run(self, args: List[str]):
        # request = PriceLoaderRequest()
        # result = PriceLoaderResult(lookup=self.print_symbol)
        #
        # if len(args) > 0:
        #   request.tickers = args
        print("Fetching tickers...")
        usecase = self.use_case_factory.fetch_tickers()
        usecase.execute()

    @staticmethod
    def print_symbol(data: dict):
        symbol = data['ticker']
        date = data["start"]
        end = data["end"]
        print(f"Fetching {symbol}: {date} -> {end}")


def main():
    # logging.basicConfig(level=logging.DEBUG)
    bootstrap(FetchTickersApp, sys.argv[1:])


if __name__ == "__main__":
    main()
