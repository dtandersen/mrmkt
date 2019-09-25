from dataclasses import dataclass
from typing import List

from mrmkt.entity.analysis import Analysis
from mrmkt.entity.finmodel import FinancialModel
from mrmkt.entity.finrep import FinancialReports


@dataclass
class BuffetModel(FinancialModel):
    @staticmethod
    def analyze(rep2: FinancialReports) -> List[Analysis]:
        analysises = []
        for rep in rep2.financial_reports:
            bal = rep.balance_sheet
            inc = rep.income_statement
            cf = rep.cash_flow
            enterprise_value = rep.enterprise_value
            close = enterprise_value.stock_price

            market_cap = (close * inc.waso)
            equity = bal.totalAssets - bal.totalLiabilities
            eps = inc.netIncome / inc.waso
            bookValue = equity / inc.waso
            priceToBookValue = close / bookValue
            pe = close / eps
            current_assets = bal.receivables + bal.inventories
            deprec = cf.deprec
            analysis = Analysis(
                symbol=inc.symbol,
                date=inc.date,
                assets=bal.totalAssets,
                current_assets=current_assets,
                liabilities=bal.totalLiabilities,
                sharesOutstanding=enterprise_value.shares_outstanding,
                netIncome=inc.netIncome,
                equity=equity,
                eps=inc.netIncome / inc.waso,
                bookValue=bookValue,
                pe=close / eps,
                priceToBookValue=close / bookValue,
                buffetNumber=priceToBookValue * pe,
                marginOfSafety=equity / market_cap,
                deprec=deprec
            )

            analysises.append(analysis)

        return analysises
