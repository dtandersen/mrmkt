"""Fundamentals import command (income-first, Tiingo as-reported)."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from mrmkt.command._shared import normalize_symbol, normalize_tag
from mrmkt.command.base import BaseResult, Command
from mrmkt.common.sql import Duplicate
from mrmkt.entity.enterprise_value import EnterpriseValue


class FundamentalsProvider(StrEnum):
    """Fundamentals providers selectable via ``--provider``."""

    TIINGO = "tiingo"


@dataclass(frozen=True)
class ImportFundamentalsOutcome:
    """Selected symbols plus the import result; the CLI renders it."""

    selected_symbols: list[str]
    result: "FundamentalsImportResult"


@dataclass
class FundamentalsImportResult:
    """Outcome of a fundamentals import (statements + enterprise value)."""

    imported: int = 0
    failed_batches: list[list[str]] = field(default_factory=list)

    @property
    def failed_symbols(self) -> list[str]:
        return [symbol for batch in self.failed_batches for symbol in batch]


@dataclass(frozen=True)
class ImportFundamentalsRequest:
    provider: str
    symbols: list[str] | None = None
    all_symbols: bool = False
    tag: str | None = None


@dataclass
class ImportFundamentalsResult(BaseResult[ImportFundamentalsOutcome]):
    pass


class ImportFundamentals(Command[ImportFundamentalsRequest, ImportFundamentalsResult]):
    """Import as-reported fundamentals into the local store.

    Symbols are fetched in batches. A batch that keeps failing after
    ``max_attempts`` is recorded in
    ``FundamentalsImportResult.failed_batches`` instead of aborting the
    whole run, so one bad batch does not discard the rest. Failed batches
    wait with exponential backoff between attempts.

    Enterprise-value rows join each daily market-cap point with the latest
    ``sharesBasic`` filing on or before that date and the latest stored
    bar close on or before that date; daily points without either are
    skipped, never zero-filled.
    """

    batch_size = 100

    def __init__(
        self,
        fundamentals_source,
        financials,
        prices,
        tickers,
        clock,
        on_progress: Callable[[int, int], None] | None = None,
        max_attempts: int = 3,
        retry_base_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.fundamentals_source = fundamentals_source
        self.financials = financials
        self.prices = prices
        self.tickers = tickers
        self.clock = clock
        self.on_progress = on_progress
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds
        self.sleep = sleep

    def execute(self, request: ImportFundamentalsRequest) -> ImportFundamentalsResult:
        if request.provider.lower() != FundamentalsProvider.TIINGO.value:
            return ImportFundamentalsResult.invalid_data(
                ["only the 'tiingo' provider is currently supported"]
            )
        selector_count = sum(
            (bool(request.symbols), request.all_symbols, request.tag is not None)
        )
        if selector_count != 1:
            return ImportFundamentalsResult.invalid_data(
                ["provide symbols, --all, or --tag"]
            )
        try:
            normalized_tag = (
                normalize_tag(request.tag) if request.tag is not None else None
            )
        except ValueError as error:
            return ImportFundamentalsResult.invalid_data([str(error)])

        if normalized_tag is not None:
            selected_symbols = self.tickers.get_symbols_by_tag(normalized_tag)
        elif request.all_symbols:
            selected_symbols = [ticker.ticker for ticker in self.tickers.get_tickers()]
        else:
            selected_symbols = list(request.symbols or [])
        try:
            selected_symbols = list(
                dict.fromkeys(normalize_symbol(symbol) for symbol in selected_symbols)
            )
        except ValueError as error:
            return ImportFundamentalsResult.invalid_data([str(error)])
        if not selected_symbols:
            return ImportFundamentalsResult.success(
                ImportFundamentalsOutcome(
                    selected_symbols=[], result=FundamentalsImportResult()
                )
            )
        end = self.clock.today()
        result = self._import_batches(selected_symbols, end)
        return ImportFundamentalsResult.success(
            ImportFundamentalsOutcome(selected_symbols=selected_symbols, result=result)
        )

    def _import_batches(
        self, symbols: list[str], end: date
    ) -> FundamentalsImportResult:
        normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        result = FundamentalsImportResult()
        total = len(normalized_symbols)
        done = 0
        for offset in range(0, total, self.batch_size):
            batch = normalized_symbols[offset : offset + self.batch_size]
            try:
                bundles = self._fetch_with_retry(batch, end)
            except Exception:
                result.failed_batches.append(batch)
                done += len(batch)
                self._report_progress(done, total)
                continue
            for symbol in batch:
                result.imported += self._store_symbol(symbol, bundles.get(symbol))
            done += len(batch)
            self._report_progress(done, total)
        return result

    def _store_symbol(self, symbol: str, bundle) -> int:
        """Store one symbol's bundle; returns the new-row count."""
        if bundle is None:
            return 0
        stored = 0
        for income in bundle.incomes:
            try:
                self.financials.add_income(income)
            except Duplicate:
                continue
            stored += 1
        for balance in bundle.balances:
            try:
                self.financials.add_balance_sheet(balance)
            except Duplicate:
                continue
            stored += 1
        for cashflow in bundle.cashflows:
            try:
                self.financials.add_cash_flow(cashflow)
            except Duplicate:
                continue
            stored += 1
        stored += self._store_enterprise_value(symbol, bundle)
        return stored

    def _store_enterprise_value(self, symbol: str, bundle) -> int:
        """Join daily caps with point-in-time shares and bar closes."""
        if not bundle.daily_caps or not bundle.shares_by_date:
            return 0
        try:
            bars = sorted(self.prices.list_prices(symbol), key=lambda bar: bar.date)
        except Exception:
            return 0
        if not bars:
            return 0
        filings = sorted(bundle.shares_by_date)
        stored = 0
        bar_index = 0
        filing_index = 0
        shares: float | None = None
        for cap in sorted(bundle.daily_caps, key=lambda point: point.date):
            while filing_index < len(filings) and filings[filing_index] <= cap.date:
                shares = bundle.shares_by_date[filings[filing_index]]
                filing_index += 1
            while bar_index + 1 < len(bars) and bars[bar_index + 1].date <= cap.date:
                bar_index += 1
            if shares is None or bars[bar_index].date > cap.date:
                continue
            try:
                self.financials.add_enterprise_value(
                    EnterpriseValue(
                        symbol=symbol,
                        date=cap.date,
                        stock_price=bars[bar_index].close,
                        shares_outstanding=shares,
                        market_cap=cap.market_cap,
                    )
                )
            except Duplicate:
                continue
            stored += 1
        return stored

    def _fetch_with_retry(self, batch: list[str], end: date) -> dict:
        attempt = 0
        while True:
            try:
                return self.fundamentals_source.get_fundamentals(batch, end)
            except Exception:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise
                self.sleep(self.retry_base_seconds * (2 ** (attempt - 1)))

    def _report_progress(self, done: int, total: int) -> None:
        if self.on_progress is not None:
            self.on_progress(done, total)
