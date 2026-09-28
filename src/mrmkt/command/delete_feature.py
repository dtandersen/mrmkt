"""Feature delete command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.base import BaseResult, Command


@dataclass(frozen=True)
class DeleteFeatureRequest:
    symbol: str
    name: str


@dataclass
class DeleteFeatureResult(BaseResult[int]):
    pass


class DeleteFeature(Command[DeleteFeatureRequest, DeleteFeatureResult]):
    """Delete all dates for one symbol+feature; reports rows removed."""

    def __init__(self, features):
        self.features = features

    def execute(self, request: DeleteFeatureRequest) -> DeleteFeatureResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return DeleteFeatureResult.invalid_data([str(error)])
        try:
            removed = self.features.delete_features(symbol, request.name.strip())
        except Exception as error:
            return DeleteFeatureResult.error([f"Failed to delete feature: {error}"])
        return DeleteFeatureResult.success(removed)
