"""Feature list command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.feature import Feature


@dataclass(frozen=True)
class ListFeaturesRequest:
    symbol: str


@dataclass
class ListFeaturesResult(BaseResult[list[Feature]]):
    pass


class ListFeatures(Command[ListFeaturesRequest, ListFeaturesResult]):
    """List stored features for one symbol, oldest first."""

    def __init__(self, features):
        self.features = features

    def execute(self, request: ListFeaturesRequest) -> ListFeaturesResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return ListFeaturesResult.invalid_data([str(error)])
        try:
            rows = self.features.list_features(symbol)
        except Exception as error:
            return ListFeaturesResult.error([f"Failed to list features: {error}"])
        return ListFeaturesResult.success(rows)
