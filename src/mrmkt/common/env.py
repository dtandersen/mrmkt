from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient

from mrmkt.common.clock import Clock
from mrmkt.repo.financials import FinancialRepository
from mrmkt.repo.prices import PriceRepository
from mrmkt.repo.tags import TickerTagRepository
from mrmkt.repo.tickers import TickerRepository
from mrmkt.repo.ticks import LiveTickSource
from mrmkt.repo.trigger_sets import TriggerSetRepository
from mrmkt.repo.triggers import TriggerRepository

if TYPE_CHECKING:
    from mrmkt.composition import CommandFactory


@dataclass
class MrMktEnvironment2:
    financials: FinancialRepository
    prices: PriceRepository
    tickers: TickerRepository
    tags: TickerTagRepository
    triggers: TriggerRepository
    trigger_sets: TriggerSetRepository
    clock: Clock
    alpaca_client: TradingClient
    alpaca_data_client: StockHistoricalDataClient
    trigger_name_generator: Callable[[], str]
    triggerset_name_generator: Callable[[], str]
    tick_source: LiveTickSource | None = None
    # Wired by the composition root right after the factory is built; never None.
    command_factory: CommandFactory = field(init=False)
