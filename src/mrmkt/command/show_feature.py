"""Feature show command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.feature import Feature


@dataclass(frozen=True)
class ShowFeatureRequest:
    symbol: str
    name: str


@dataclass
class ShowFeatureResult(BaseResult[Feature]):
    pass


class ShowFeature(Command[ShowFeatureRequest, ShowFeatureResult]):
    """Return the latest stored value for one symbol+feature."""

    def __init__(self, features):
        self.features = features

    def execute(self, request: ShowFeatureRequest) -> ShowFeatureResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return ShowFeatureResult.invalid_data([str(error)])
        try:
            rows = self.features.list_features(symbol, request.name.strip())
        except Exception as error:
            return ShowFeatureResult.error([f"Failed to show feature: {error}"])
        if not rows:
            return ShowFeatureResult.not_found(
                [f"no feature {request.name!r} for {symbol!r}"]
            )
        return ShowFeatureResult.success(rows[-1])
