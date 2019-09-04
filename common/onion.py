import datetime
from abc import abstractmethod
from typing import List, Optional

from entity.analysis import Analysis
from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
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
    def list_balance_sheets(self, symbol) -> List[BalanceSheet]:
        raise NotImplementedError

    @abstractmethod
    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        raise NotImplementedError

    @abstractmethod
    def get_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
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
    def add_price(self, price: StockPrice) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_analysis(self, analysis: Analysis) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_analysis(self, symbol: str, date: datetime.date) -> None:
        raise NotImplementedError
