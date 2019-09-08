from dataclasses import dataclass

from common.inmemfinrepo import FinancialRepository


@dataclass
class RunModelRequest:
    symbol: str
    model_class: any


class RunModel:
    def __init__(self, financial_repository: FinancialRepository):
        self.financial_repository = financial_repository

    def execute(self, req: RunModelRequest) -> None:
        symbol = req.symbol
        model = req.model_class()

        financial_reports = self.financial_repository.list_financial_reports(symbol)

        results = model.analyze(financial_reports)

        for analysis in results:
            self.financial_repository.delete_analysis(analysis.symbol, analysis.date)
            self.financial_repository.add_analysis(analysis)
