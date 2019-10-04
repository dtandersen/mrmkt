from abc import ABC, ABCMeta

from mrmkt.repo.finrepo import FinancialRepository, ReadOnlyFinancialRepository
from mrmkt.repo.prices import PriceRepository, ReadOnlyPriceRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository


class ReadOnlyAllRepository(ReadOnlyFinancialRepository, ReadOnlyPriceRepository, ReadOnlyTickerRepository,
                            metaclass=ABCMeta):
    pass


class AllRepository(FinancialRepository, PriceRepository,metaclass=ABCMeta):
    pass
