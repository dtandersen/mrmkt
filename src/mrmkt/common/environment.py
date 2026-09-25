from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Any, Callable

from mrmkt.common.clock import Clock
from mrmkt.composition import CommandFactory, RepositoryFactory
from mrmkt.repo.provider import MarketDataProvider, ReadOnlyMarketDataProvider


class MrMktEnvironment(ABC):
    @property
    @abstractmethod
    def local(self) -> MarketDataProvider:
        pass

    @property
    @abstractmethod
    def remote(self) -> ReadOnlyMarketDataProvider:
        pass

    @property
    @abstractmethod
    def clock(self) -> Clock:
        pass

@dataclass
class MrMktEnvironment2:
    repository_factory: RepositoryFactory 
    clock: Any | None 
    alpaca_client: Any | None
    alpaca_data_client: Any | None
    trigger_name_generator: Callable[[], str] | None 
    triggerset_name_generator: Callable[[], str] | None 
    command_factory: CommandFactory | None
