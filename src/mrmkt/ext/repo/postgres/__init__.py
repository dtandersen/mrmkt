"""Narrow Postgres repositories, one per capability."""

from mrmkt.ext.repo.postgres.financials import PostgresFinancialRepository
from mrmkt.ext.repo.postgres.prices import PostgresPriceRepository
from mrmkt.ext.repo.postgres.tags import PostgresTagRepository
from mrmkt.ext.repo.postgres.tickers import PostgresTickerRepository
from mrmkt.ext.repo.postgres.trigger_sets import PostgresTriggerSetRepository
from mrmkt.ext.repo.postgres.triggers import PostgresTriggerRepository

__all__ = [
    "PostgresFinancialRepository",
    "PostgresPriceRepository",
    "PostgresTagRepository",
    "PostgresTickerRepository",
    "PostgresTriggerRepository",
    "PostgresTriggerSetRepository",
]
