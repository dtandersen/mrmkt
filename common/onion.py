import datetime
from abc import abstractmethod
from typing import List, Optional

from entity.analysis import Analysis
from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from entity.finrep import FinancialReport, FinancialReports
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class ReadOnlyFinancialRepository:
    @abstractmethod
    def get_symbols(self) -> Optional[List[str]]:
        raise NotImplementedError

    @abstractmethod
    def get_income_statement(self, symbol: str, date: datetime.date) -> List[IncomeStatement]:
        raise NotImplementedError

    @abstractmethod
    def list_income_statements(self, symbol: str) -> List[IncomeStatement]:
        raise NotImplementedError

    @abstractmethod
    def get_balance_sheet(self, symbol, date: datetime.date) -> List[BalanceSheet]:
        raise NotImplementedError

    @abstractmethod
    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        raise NotImplementedError

    @abstractmethod
    def list_balance_sheets(self, symbol) -> List[BalanceSheet]:
        raise NotImplementedError

    @abstractmethod
    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        raise NotImplementedError

    @abstractmethod
    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        raise NotImplementedError

    @abstractmethod
    def list_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        raise NotImplementedError

    @abstractmethod
    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        raise NotImplementedError

    @abstractmethod
    def list_prices(self, symbol: str) -> List[StockPrice]:
        raise NotImplementedError


class FinancialRepository(ReadOnlyFinancialRepository):
    @abstractmethod
    def add_income(self, income_statement: IncomeStatement) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_cash_flow(self, cash_flow: CashFlow):
        raise NotImplementedError

    @abstractmethod
    def add_enterprise_value(self, enterprise_value: EnterpriseValue):
        raise NotImplementedError

    @abstractmethod
    def add_price(self, price: StockPrice) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_analysis(self, analysis: Analysis) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_analysis(self, symbol: str, date: datetime.date) -> None:
        raise NotImplementedError

    def list_financial_reports(self, symbol: str) -> FinancialReports:
        incs = self.list_income_statements(symbol)
        bals = self.list_balance_sheets(symbol)
        cfs = self.list_cash_flows(symbol)
        evs = self.list_enterprise_value(symbol)

        reps = []
        for i in range(len(incs)):
            inc = incs[i]
            bal = bals[i]
            cf = cfs[i]
            ev = evs[i]
            reps.append(FinancialReport(
                symbol=symbol,
                date=inc.date,
                income_statement=inc,
                balance_sheet=bal,
                cash_flow=cf,
                enterprise_value=ev
            ))

        return FinancialReports(symbol=symbol, financial_reports=reps)