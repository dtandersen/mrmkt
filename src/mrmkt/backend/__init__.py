"""Mr Market backend interface (whole service, not one resource).

A backend IS-A bundle of repository interfaces: commands keep their
narrow parameters while composition passes a single object everywhere.
Postgres satisfies this with the existing shared repository; the API
backend implements it over HTTP, resource by resource.
"""

from abc import ABC, abstractmethod

from mrmkt.repo.tickers import TickerRepository
from mrmkt.repo.triggers import TriggerRepository

__all__ = ["MrMktBackend"]


class MrMktBackend(TriggerRepository, TickerRepository, ABC):
    """Trigger plus symbol catalogs with an explicit release."""

    @abstractmethod
    def close(self) -> None:
        """Release backend resources, if any."""
