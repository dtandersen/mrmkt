"""Live trade-tick source contract."""

import datetime
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Tick:
    symbol: str
    price: float
    at: datetime.datetime


class LiveTickSource(ABC):
    """Yield live trade ticks for one symbol, holding open until cancelled.

    Declared as a plain method returning an async iterator: overrides
    are ``async def`` generators, whose type is an async iterator.
    """

    @abstractmethod
    def subscribe(self, symbol: str) -> AsyncIterator[Tick]:
        pass
