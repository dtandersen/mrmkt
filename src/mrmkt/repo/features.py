"""Feature repository interfaces."""

import abc
import datetime

from mrmkt.entity.feature import Feature


class ReadOnlyFeatureRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def list_features(
        self,
        symbol: str,
        feature: str | None = None,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[Feature]:
        """Features for one symbol, oldest first, optionally filtered."""


class FeatureRepository(ReadOnlyFeatureRepository, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_feature(self, feature: Feature):
        """Store one feature value; Duplicate on (symbol, exchange, feature, date)."""

    @abc.abstractmethod
    def delete_features(self, symbol: str, feature: str) -> int:
        """Delete all dates for one symbol+feature; returns rows removed."""
