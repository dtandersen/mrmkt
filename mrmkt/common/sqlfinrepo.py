import datetime
from dataclasses import dataclass
from typing import List

from mrmkt.common.sql import SqlClient, JsonField
from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.finrep import FinancialReport
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.repo.financials import FinancialRepository
from mrmkt.repo.prices import PriceRepository
from mrmkt.repo.tickers import TickerRepository


class SqlFinancialRepository(FinancialRepository, PriceRepository, TickerRepository):
    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def list_balance_sheets(self, symbol: str):
        return self.sql_client.select("select * " +
                                      "from balance_sheet "
                                      f"where symbol = '{symbol}'",
                                      self.to_balance_sheet)

    def to_balance_sheet(self, row):
        return BalanceSheet(
            symbol=row["symbol"],
            date=row["date"],
            totalAssets=row["total_assets"],
            totalLiabilities=row["total_liabilities"])

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        row = BalanceSheetRow(
            symbol=balance_sheet.symbol,
            date=balance_sheet.date,
            total_assets=balance_sheet.totalAssets,
            total_liabilities=balance_sheet.totalLiabilities
        )

        self.sql_client.insert("balance_sheet", row)

    def get_income_statements(self, symbol: str) -> List[IncomeStatement]:
        return self.sql_client.select("select * " +
                                      "from income_stmt "
                                      f"where symbol = '{symbol}'",
                                      self.to_income_statement)

    def to_income_statement(self, row):
        return IncomeStatement(
            symbol=row["symbol"],
            date=row["date"],
            netIncome=row["net_income"],
            waso=row["waso"],
            consolidated_net_income=-1
        )

    def add_income(self, income_statement: IncomeStatement):
        row = IncomeStatementRow(
            symbol=income_statement.symbol,
            date=income_statement.date,
            net_income=income_statement.netIncome,
            waso=income_statement.waso
        )

        self.sql_client.insert("income_stmt", row)

    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        row = self.sql_client.select(
            "select * "
            "from cash_flow "
            f"where symbol = '{symbol}' "
            f"and date = '{date}'",
            self.map_to_cash_flow)

        return row[0]

    def map_to_cash_flow(self, row) -> CashFlow:
        return CashFlow(
            symbol=row['symbol'],
            date=row['date'],
            operating_cash_flow=row['operating_cash_flow'],
            capital_expenditure=row['capital_expenditure'],
            free_cash_flow=row['free_cash_flow'],
            dividend_payments=row['dividend_payments']
        )

    def add_cash_flow(self, cash_flow: CashFlow):
        row = CashFlowRow(
            symbol=cash_flow.symbol,
            date=cash_flow.date,
            operating_cash_flow=cash_flow.operating_cash_flow,
            capital_expenditure=cash_flow.capital_expenditure,
            free_cash_flow=cash_flow.free_cash_flow,
            dividend_payments=cash_flow.dividend_payments
        )

        self.sql_client.insert("cash_flow", row)

    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        row = self.sql_client.select(
            "select * "
            "from enterprise_value "
            f"where symbol = '{symbol}' "
            f"and date = '{date}'",
            self.map_to_enterprise_value)

        return row[0]

    def map_to_enterprise_value(self, row) -> EnterpriseValue:
        return EnterpriseValue(
            symbol=row['symbol'],
            date=row['date'],
            stock_price=row['stock_price'],
            shares_outstanding=row['shares_outstanding'],
            market_cap=row['market_cap']
        )

    def add_enterprise_value(self, enterprise_value: EnterpriseValue):
        row = EnterpriseValueRow(
            symbol=enterprise_value.symbol,
            date=enterprise_value.date,
            stock_price=enterprise_value.stock_price,
            shares_outstanding=enterprise_value.shares_outstanding,
            market_cap=enterprise_value.market_cap
        )

        self.sql_client.insert("enterprise_value", row)

    def add_analysis(self, analysis: Analysis):
        row = AnalysisRow(
            symbol=analysis.symbol,
            date=analysis.date,
            net_income=analysis.netIncome,
            buffet_number=analysis.buffetNumber,
            price_to_book_value=analysis.priceToBookValue,
            shares_outstanding=analysis.sharesOutstanding,
            liabilities=analysis.liabilities,
            assets=analysis.assets,
            margin_of_safety=analysis.marginOfSafety,
            book_value=analysis.bookValue,
            eps=analysis.eps,
            equity=analysis.equity,
            pe=analysis.pe
        )

        self.sql_client.insert("analysis", row)

    def delete_analysis(self, symbol: str, date: datetime.date):
        self.sql_client.delete(
            "delete from analysis "
            f"where symbol = '{symbol}' "
            f"and date = '{date}'")

    def add_price(self, price: StockPrice):
        row = PriceRow(
            symbol=price.symbol,
            date=price.date,
            open=price.open,
            high=price.high,
            low=price.low,
            close=price.close,
            volume=price.volume)

        self.sql_client.insert("daily_price", row)

    def list_prices(self, ticker: str, start: datetime.date = None, end: datetime.date = None) -> List[StockPrice]:
        start_sql = ""
        end_sql = ""
        if start is not None:
            start_str = start.strftime("%Y-%m-%d")
            start_sql = f"and date >= '{start_str}' "

        if end is not None:
            end_str = end.strftime("%Y-%m-%d")
            end_sql = f"and date <= '{end_str}' "

        rows = self.sql_client.select(
            "select * " +
            "from daily_price " +
            f"where symbol = '{ticker}' " +
            start_sql +
            end_sql +
            "order by date asc",
            self.price_mapper)

        return rows

    def get_price(self, symbol: str, date: str) -> StockPrice:
        rows = self.sql_client.select("select * " +
                                      "from daily_price " +
                                      f"where symbol = '{symbol}' " +
                                      f"and date = '{date}'",
                                      self.price_mapper)

        return rows[0]

    def price_mapper(self, row):
        return StockPrice(
            symbol=row["symbol"],
            date=row["date"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"]
        )

    def get_price_on_or_after(self, symbol: str, date: str) -> StockPrice:
        rows = self.sql_client.select("select * " +
                                      "from daily_price " +
                                      f"where symbol = '{symbol}' " +
                                      f"and date >= '{date}'",
                                      self.price_mapper)

        return rows[0]

    def insert_financial(self, rep: FinancialReport):
        f = FinancialRow(
            symbol="abc",
            date=datetime.date(2019, 1, 2),
            data="{}"
        )
        self.sql_client.insert2("financials", f)

    def get_symbols(self) -> List[str]:
        rows = self.sql_client.select(
            "select distinct symbol " +
            "from daily_price ",
            self.symbol_mapper)

        return rows

    def symbol_mapper(self, row):
        return row["symbol"]

    def get_tickers(self) -> List[Ticker]:
        rows = self.sql_client.select(
            "select * " +
            "from ticker",
            self.ticker_mapper)

        return rows

    def ticker_mapper(self, row):
        return Ticker(
            ticker=row["ticker"],
            exchange=row["exchange"],
            type=row["type"]
        )

    def add_ticker(self, ticker: Ticker):
        row = TickerRow(
            ticker=ticker.ticker,
            exchange=ticker.exchange,
            type=ticker.type
        )

        self.sql_client.insert("ticker", row)

    def get_income_statement(self, symbol: str, date: datetime.date) -> List[IncomeStatement]:
        raise NotImplementedError

    def list_income_statements(self, symbol: str) -> List[IncomeStatement]:
        raise NotImplementedError

    def get_balance_sheet(self, symbol, date: datetime.date) -> List[BalanceSheet]:
        raise NotImplementedError

    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        raise NotImplementedError

    def list_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        raise NotImplementedError


@dataclass
class BalanceSheetRow:
    symbol: str
    date: datetime.date
    total_assets: float
    total_liabilities: float


@dataclass
class IncomeStatementRow:
    symbol: str
    date: datetime.date
    net_income: float
    waso: int


@dataclass
class CashFlowRow:
    symbol: str
    date: datetime.date
    operating_cash_flow: float
    capital_expenditure: float
    free_cash_flow: float
    dividend_payments: float


@dataclass
class EnterpriseValueRow:
    symbol: str
    date: datetime.date
    stock_price: float
    shares_outstanding: float
    market_cap: float


@dataclass
class AnalysisRow:
    symbol: str
    date: datetime.date
    net_income: float
    buffet_number: float
    price_to_book_value: float
    shares_outstanding: float
    liabilities: float
    assets: float
    margin_of_safety: float
    book_value: float
    eps: float
    equity: float
    pe: float


@dataclass
class PriceRow:
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class FinancialRow:
    symbol: str
    date: datetime.date
    data: JsonField


@dataclass
class SymbolRow:
    symbol: str


@dataclass
class TickerRow:
    ticker: str
    exchange: str
    type: str
