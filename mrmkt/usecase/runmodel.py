from dataclasses import dataclass

from mrmkt.repo.provider import ReadOnlyMarketDataProvider


@dataclass
class RunModelRequest:
    symbol: str
    model_class: any


class RunModel:
    def __init__(self, financial_repository: ReadOnlyMarketDataProvider):
        self.financial_repository = financial_repository

    def execute(self, req: RunModelRequest) -> None:
        symbol = req.symbol
        model = req.model_class()

        financial_reports = self.financial_repository.financials.list_financial_reports(symbol)

        results = model.analyze(financial_reports)

        for analysis in results:
            self.financial_repository.financials.delete_analysis(analysis.symbol, analysis.date)
            self.financial_repository.financials.add_analysis(analysis)
