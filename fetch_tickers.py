import sys
from typing import List

from bootstrapper import bootstrap
from mrmkt.apprunner.runner import App
from mrmkt.usecase.fetch_tickers import FetchTickersResult
from use_case_factory import MrMktUseCaseFactory

class AppFetchTickersResult(FetchTickersResult):
    def on_tickers_updated(self, count: int):
        pass


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
        usecase.result = FetchTickersResult(on_tickers_updated=FetchTickersApp.print_symbol)
        usecase.execute()

    @staticmethod
    def print_symbol(count: int):
        print(f"Fetched {count} tickers")


def main():
    # logging.basicConfig(level=logging.DEBUG)
    bootstrap(FetchTickersApp, sys.argv[1:])


if __name__ == "__main__":
    main()
