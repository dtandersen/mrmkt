"""Realtime price gateway contracts (DTOs and transport interfaces)."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mrmkt.entity.trading import Account, Position, TradingOrder


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

    def close(self) -> None:
        """Stop blocking subscribe calls so consumer threads can exit."""
        return None


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


class TradingGateway(ABC):
    """Paper-account trading surface (Alpaca paper endpoint only)."""

    @abstractmethod
    def list_positions(self) -> list[Position]:
        """Return all open positions."""

    @abstractmethod
    def list_orders(self, status: str = "open") -> list[TradingOrder]:
        """Return orders filtered by status (open, closed, all)."""

    @abstractmethod
    def get_order(self, order_id: str) -> TradingOrder | None:
        """Return one order by id, or None when unknown."""

    @abstractmethod
    def submit_limit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        limit_price: float,
        stop_price: float | None = None,
        time_in_force: str = "day",
    ) -> TradingOrder:
        """Submit a DAY limit order, OTO stop-loss when stop_price given.

        House rule: orders live one session (``day``). ``gtc`` is an
        explicit escape hatch, never the default."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> None:
        """Cancel one open order; raises KeyError when unknown."""

    @abstractmethod
    def get_account(self) -> Account:
        """Return the paper-account balance snapshot."""


class QuoteGateway(ABC):
    """One-shot latest-quote surface (Alpaca data feed)."""

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Quote:
        """Return the latest quote; raises KeyError when unknown."""
