import datetime
from abc import abstractmethod, ABC, ABCMeta
from typing import List

from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.finrep import FinancialReports, FinancialReport
from mrmkt.entity.income_statement import IncomeStatement


class ReadOnlyFinancialRepository(metaclass=ABCMeta):
    @abstractmethod
    def get_income_statement(self, symbol: str, date: datetime.date) -> List[IncomeStatement]:
        pass

    @abstractmethod
    def list_income_statements(self, symbol: str) -> List[IncomeStatement]:
        pass

    @abstractmethod
    def get_balance_sheet(self, symbol, date: datetime.date) -> List[BalanceSheet]:
        pass

    @abstractmethod
    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        pass

    @abstractmethod
    def list_balance_sheets(self, symbol) -> List[BalanceSheet]:
        pass

    @abstractmethod
    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        pass

    @abstractmethod
    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        pass

    @abstractmethod
    def list_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        pass


class FinancialRepository(ReadOnlyFinancialRepository, metaclass=ABCMeta):
    @abstractmethod
    def add_income(self, income_statement: IncomeStatement) -> None:
        pass

    @abstractmethod
    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        pass

    @abstractmethod
    def add_cash_flow(self, cash_flow: CashFlow):
        pass

    @abstractmethod
    def add_enterprise_value(self, enterprise_value: EnterpriseValue):
        pass

    @abstractmethod
    def add_analysis(self, analysis: Analysis) -> None:
        pass

    @abstractmethod
    def delete_analysis(self, symbol: str, date: datetime.date) -> None:
        pass

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
