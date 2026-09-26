import datetime
import re
from contextlib import suppress
from dataclasses import dataclass

from mrmkt.common.sql import Duplicate, SqlClient
from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.finrep import FinancialReport
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import (
    FREQUENCIES,
    OPERATORS,
    Trigger,
    normalize_trigger_indicator,
)
from mrmkt.repo.financials import FinancialRepository
from mrmkt.repo.prices import PriceRepository
from mrmkt.repo.tags import TickerTagRepository
from mrmkt.repo.tickers import TickerRepository
from mrmkt.repo.trigger_sets import TriggerSetNotFound, TriggerSetRepository
from mrmkt.repo.triggers import TriggerRepository


class SqlFinancialRepository(
    FinancialRepository,
    PriceRepository,
    TickerRepository,
    TickerTagRepository,
    TriggerRepository,
    TriggerSetRepository,
):
    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def list_balance_sheets(self, symbol: str):
        return self.sql_client.select(
            "select * " + "from balance_sheet where symbol = %s",
            self.to_balance_sheet,
            (symbol,),
        )

    def to_balance_sheet(self, row):
        return BalanceSheet(
            symbol=row["symbol"],
            date=row["date"],
            totalAssets=row["total_assets"],
            totalLiabilities=row["total_liabilities"],
        )

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        row = BalanceSheetRow(
            symbol=balance_sheet.symbol,
            date=balance_sheet.date,
            total_assets=balance_sheet.totalAssets,
            total_liabilities=balance_sheet.totalLiabilities,
        )

        self.sql_client.insert("balance_sheet", row)

    def get_income_statements(self, symbol: str) -> list[IncomeStatement]:
        return self.sql_client.select(
            "select * " + "from income_stmt where symbol = %s",
            self.to_income_statement,
            (symbol,),
        )

    def to_income_statement(self, row):
        return IncomeStatement(
            symbol=row["symbol"],
            date=row["date"],
            netIncome=row["net_income"],
            waso=row["waso"],
            consolidated_net_income=-1,
        )

    def add_income(self, income_statement: IncomeStatement):
        row = IncomeStatementRow(
            symbol=income_statement.symbol,
            date=income_statement.date,
            net_income=income_statement.netIncome,
            waso=income_statement.waso,
        )

        self.sql_client.insert("income_stmt", row)

    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        row = self.sql_client.select(
            "select * from cash_flow where symbol = %s and date = %s",
            self.map_to_cash_flow,
            (symbol, date),
        )

        return row[0]

    def map_to_cash_flow(self, row) -> CashFlow:
        return CashFlow(
            symbol=row["symbol"],
            date=row["date"],
            operating_cash_flow=row["operating_cash_flow"],
            capital_expenditure=row["capital_expenditure"],
            free_cash_flow=row["free_cash_flow"],
            dividend_payments=row["dividend_payments"],
        )

    def add_cash_flow(self, cash_flow: CashFlow):
        row = CashFlowRow(
            symbol=cash_flow.symbol,
            date=cash_flow.date,
            operating_cash_flow=cash_flow.operating_cash_flow,
            capital_expenditure=cash_flow.capital_expenditure,
            free_cash_flow=cash_flow.free_cash_flow,
            dividend_payments=cash_flow.dividend_payments,
        )

        self.sql_client.insert("cash_flow", row)

    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        row = self.sql_client.select(
            "select * from enterprise_value where symbol = %s and date = %s",
            self.map_to_enterprise_value,
            (symbol, date),
        )

        return row[0]

    def map_to_enterprise_value(self, row) -> EnterpriseValue:
        return EnterpriseValue(
            symbol=row["symbol"],
            date=row["date"],
            stock_price=row["stock_price"],
            shares_outstanding=row["shares_outstanding"],
            market_cap=row["market_cap"],
        )

    def add_enterprise_value(self, enterprise_value: EnterpriseValue):
        row = EnterpriseValueRow(
            symbol=enterprise_value.symbol,
            date=enterprise_value.date,
            stock_price=enterprise_value.stock_price,
            shares_outstanding=enterprise_value.shares_outstanding,
            market_cap=enterprise_value.market_cap,
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
            pe=analysis.pe,
        )

        self.sql_client.insert("analysis", row)

    def delete_analysis(self, symbol: str, date: datetime.date):
        self.sql_client.delete(
            "delete from analysis where symbol = %s and date = %s", (symbol, date)
        )

    def add_price(self, price: StockPrice):
        row = PriceRow(
            symbol=price.symbol,
            date=price.date,
            open=price.open,
            high=price.high,
            low=price.low,
            close=price.close,
            volume=price.volume,
        )

        self.sql_client.insert("daily_price", row)

    def list_prices(
        self,
        ticker: str,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[StockPrice]:
        start_sql = ""
        end_sql = ""
        params: list = [ticker]
        if start is not None:
            start_sql = "and date >= %s "
            params.append(start.strftime("%Y-%m-%d"))

        if end is not None:
            end_sql = "and date <= %s "
            params.append(end.strftime("%Y-%m-%d"))

        rows = self.sql_client.select(
            "select * "
            + "from daily_price "
            + "where symbol = %s "
            + start_sql
            + end_sql
            + "order by date asc",
            self.price_mapper,
            tuple(params),
        )

        return rows

    def list_prices_for_symbols(
        self,
        tickers: list[str],
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[StockPrice]:
        normalized = []
        for ticker in tickers:
            symbol = ticker.strip().upper()
            if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", symbol) is None:
                raise ValueError(f"invalid stock symbol: {ticker}")
            normalized.append(symbol)
        if not normalized:
            return []
        start_sql = ""
        end_sql = ""
        params: list = [tuple(normalized)]
        if start is not None:
            start_sql = "and date >= %s "
            params.append(start.strftime("%Y-%m-%d"))
        if end is not None:
            end_sql = "and date <= %s "
            params.append(end.strftime("%Y-%m-%d"))
        return self.sql_client.select(
            "select * "
            + "from daily_price "
            + "where symbol in %s "
            + start_sql
            + end_sql
            + "order by symbol asc, date asc",
            self.price_mapper,
            tuple(params),
        )

    def get_price(self, symbol: str, date: str) -> StockPrice:
        rows = self.sql_client.select(
            "select * " + "from daily_price " + "where symbol = %s " + "and date = %s",
            self.price_mapper,
            (symbol, date),
        )

        return rows[0]

    def price_mapper(self, row):
        return StockPrice(
            symbol=row["symbol"],
            date=row["date"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        rows = self.sql_client.select(
            "select * " + "from daily_price " + "where symbol = %s " + "and date >= %s",
            self.price_mapper,
            (symbol, date),
        )

        return rows[0]

    def insert_financial(self, rep: FinancialReport):
        f = FinancialRow(symbol="abc", date=datetime.date(2019, 1, 2), data="{}")
        self.sql_client.insert("financials", f)

    def get_symbols(self) -> list[str]:
        rows = self.sql_client.select(
            "select distinct symbol " + "from daily_price ", self.symbol_mapper
        )

        return rows

    def symbol_mapper(self, row):
        return row["symbol"]

    def get_tickers(self) -> list[Ticker]:
        rows = self.sql_client.select("select * " + "from ticker", self.ticker_mapper)

        return rows

    def ticker_mapper(self, row):
        return Ticker(ticker=row["ticker"], exchange=row["exchange"], type=row["type"])

    def add_ticker(self, ticker: Ticker):
        row = TickerRow(
            ticker=ticker.ticker, exchange=ticker.exchange, type=ticker.type
        )

        self.sql_client.insert("ticker", row)

    def add_tag(self, ticker: str, exchange: str, tag: str) -> None:
        self.sql_client.insert("ticker_tag", TickerTagRow(ticker, exchange, tag))

    def remove_tag(self, ticker: str, exchange: str, tag: str) -> bool:
        return self.sql_client.delete(
            "delete from ticker_tag where ticker = %s and exchange = %s and tag = %s",
            (ticker, exchange, tag),
        )

    def get_tags(self, ticker: str, exchange: str) -> list[str]:
        rows = self.sql_client.select(
            "select ticker, exchange, tag from ticker_tag",
            lambda row: row,
        )
        return sorted(
            row["tag"]
            for row in rows
            if row["ticker"] == ticker and row["exchange"] == exchange
        )

    def list_tickers_by_tag(self, tag: str) -> list[Ticker]:
        rows = self.sql_client.select(
            "select ticker, exchange, tag from ticker_tag",
            lambda row: row,
        )
        tagged = {(row["ticker"], row["exchange"]) for row in rows if row["tag"] == tag}
        return sorted(
            (
                ticker
                for ticker in self.get_tickers()
                if (ticker.ticker, ticker.exchange) in tagged
            ),
            key=lambda ticker: (ticker.ticker, ticker.exchange),
        )

    def get_symbols_by_tag(self, tag: str) -> list[str]:
        return sorted({ticker.ticker for ticker in self.list_tickers_by_tag(tag)})

    def list_triggers(self, enabled_only: bool = False) -> list[Trigger]:
        query = "select * from trigger order by id asc"
        if enabled_only:
            query = "select * from trigger where enabled = %s order by id asc"
            return self.sql_client.select(query, self.trigger_mapper, (True,))
        return self.sql_client.select(query, self.trigger_mapper)

    def trigger_mapper(self, row) -> Trigger:
        # DB column was renamed signal -> indicator in migration13;
        # accept both for rolling upgrades.
        return Trigger(
            id=row["id"],
            name=row["name"],
            symbol=row["symbol"],
            indicator=row.get("indicator", row.get("signal")),
            operator=row["operator"],
            value=row["value"],
            frequency=row["frequency"],
            expires_at=row["expires_at"],
            message=row["message"],
            enabled=row["enabled"],
        )

    def add_trigger(self, trigger: Trigger) -> Trigger:
        self._validate_trigger(trigger)
        if not trigger.name or not trigger.name.strip():
            raise ValueError("trigger name must not be blank")
        row = TriggerRow(
            name=trigger.name.strip(),
            symbol=trigger.symbol,
            indicator=trigger.indicator,
            operator=trigger.operator,
            value=trigger.value,
            frequency=trigger.frequency,
            expires_at=trigger.expires_at,
            message=trigger.message,
            enabled=trigger.enabled,
        )
        try:
            self.sql_client.insert("trigger", row)
        except Duplicate as error:
            raise ValueError(
                f"trigger already exists for {trigger.symbol} {trigger.indicator} {trigger.operator}"
            ) from error
        rows = self.sql_client.select(
            "select * from trigger where symbol = %s and indicator = %s and operator = %s",
            self.trigger_mapper,
            (trigger.symbol, trigger.indicator, trigger.operator),
        )
        return rows[0]

    def remove_trigger(self, trigger_id: int) -> bool:
        return self.sql_client.delete(
            "delete from trigger where id = %s",
            (trigger_id,),
        )

    def set_trigger_enabled(self, trigger_id: int, enabled: bool) -> bool:
        rows = self.sql_client.select(
            "select * from trigger where id = %s",
            self.trigger_mapper,
            (trigger_id,),
        )
        if not rows:
            return False
        current = rows[0]
        self.sql_client.delete(
            "delete from trigger where id = %s",
            (trigger_id,),
        )
        updated = TriggerRow(
            name=current.name,
            symbol=current.symbol,
            indicator=current.indicator,
            operator=current.operator,
            value=current.value,
            frequency=current.frequency,
            expires_at=current.expires_at,
            message=current.message,
            enabled=enabled,
        )
        self.sql_client.insert("trigger", updated)
        return True

    def create_set(self, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("trigger set name must not be blank")
        cleaned = name.strip()
        try:
            self.sql_client.insert("trigger_set", TriggerSetRow(cleaned))
        except Duplicate as error:
            raise ValueError(f"trigger set {cleaned!r} already exists") from error
        return cleaned

    def add_to_set(self, set_name: str, trigger_name: str) -> None:
        sets = self.sql_client.select(
            "select name from trigger_set where name = %s",
            lambda row: row["name"],
            (set_name,),
        )
        if not sets:
            raise TriggerSetNotFound(set_name)
        triggers = self.sql_client.select(
            "select name from trigger where name = %s",
            lambda row: row["name"],
            (trigger_name,),
        )
        if not triggers:
            raise ValueError(f"no trigger with name {trigger_name!r}")
        with suppress(Duplicate):
            self.sql_client.insert(
                "trigger_set_member", TriggerSetMemberRow(set_name, trigger_name)
            )

    def remove_from_set(self, set_name: str, trigger_name: str) -> bool:
        return self.sql_client.delete(
            "delete from trigger_set_member where set_name = %s and trigger_name = %s",
            (set_name, trigger_name),
        )

    def list_set_members(self, set_name: str) -> list[str]:
        sets = self.sql_client.select(
            "select name from trigger_set where name = %s",
            lambda row: row["name"],
            (set_name,),
        )
        if not sets:
            raise TriggerSetNotFound(set_name)
        return self.sql_client.select(
            "select trigger_name from trigger_set_member "
            "where set_name = %s order by trigger_name asc",
            lambda row: row["trigger_name"],
            (set_name,),
        )

    @staticmethod
    def _validate_trigger(trigger: Trigger) -> None:
        if trigger.operator not in OPERATORS:
            raise ValueError(f"{trigger.operator!r} is an invalid operator")
        if trigger.frequency not in FREQUENCIES:
            raise ValueError(f"{trigger.frequency!r} is an invalid frequency")
        normalize_trigger_indicator(trigger.indicator)

    def get_income_statement(
        self, symbol: str, date: datetime.date
    ) -> list[IncomeStatement]:
        raise NotImplementedError

    def list_income_statements(self, symbol: str) -> list[IncomeStatement]:
        raise NotImplementedError

    def get_balance_sheet(self, symbol, date: datetime.date) -> list[BalanceSheet]:
        raise NotImplementedError

    def list_cash_flows(self, symbol: str) -> list[CashFlow]:
        raise NotImplementedError

    def list_enterprise_value(self, symbol: str) -> list[EnterpriseValue]:
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
    data: str


@dataclass
class SymbolRow:
    symbol: str


@dataclass
class TickerRow:
    ticker: str
    exchange: str
    type: str


@dataclass
class TickerTagRow:
    ticker: str
    exchange: str
    tag: str


@dataclass
class TriggerRow:
    name: str
    symbol: str
    indicator: str
    operator: str
    value: float | None
    frequency: str
    expires_at: datetime.date | None
    message: str
    enabled: bool


@dataclass
class TriggerSetRow:
    name: str


@dataclass
class TriggerSetMemberRow:
    set_name: str
    trigger_name: str
