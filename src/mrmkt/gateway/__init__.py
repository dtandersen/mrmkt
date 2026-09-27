"""Realtime price gateway contracts (DTOs and transport interfaces)."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Quote:
    """Normalized level-one quote from the selected price feed."""

    symbol: str
    bid: float
    ask: float
    timestamp: datetime


class PriceSource(Protocol):
    """Live source that subscribes to symbols and emits normalized quotes."""

    def subscribe(
        self,
        symbols: list[str],
        feed: str,
        *,
        on_quote: Callable[[Quote], None],
    ) -> None:
        """Subscribe and call the handler as quotes arrive."""


class MessageQueue(ABC):
    """Queue transport for realtime price events."""

    @abstractmethod
    def subscribe(self, subject: str, *, on_event: Callable[..., None]) -> None:
        """Attach to the subject; call the handler per message."""

    @abstractmethod
    def publish(self, subject: str, event: Quote) -> None:
        """Broadcast one price event to the subject's consumers."""


class PriceProvider(ABC):
    """Push source of live quotes."""

    @abstractmethod
    def subscribe(
        self, symbols: list[str], *, on_quote: Callable[[Quote], None]
    ) -> None:
        """Attach, push each quote to the handler, and block.

        Must not return while the stream is alive: worker threads live
        inside this call, so a register-and-return implementation would
        silently end streaming. Ends on close/KeyboardInterrupt.
        """

    @abstractmethod
    def close(self) -> None:
        """Release the stream; unblocks subscribe so threads can exit."""
