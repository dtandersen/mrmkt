"""Feature create command."""

import datetime
from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol, parse_cli_date
from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.feature import Feature


@dataclass(frozen=True)
class CreateFeatureRequest:
    symbol: str
    assignment: str
    date: str | None = None


@dataclass
class CreateFeatureResult(BaseResult[Feature]):
    pass


class CreateFeature(Command[CreateFeatureRequest, CreateFeatureResult]):
    """Store one feature value; resolves the exchange from the catalog."""

    def __init__(self, features, tickers, clock):
        self.features = features
        self.tickers = tickers
        self.clock = clock

    def execute(self, request: CreateFeatureRequest) -> CreateFeatureResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return CreateFeatureResult.invalid_data([str(error)])
        name, equals, raw = request.assignment.partition("=")
        name = name.strip()
        if not equals or not name or not raw.strip():
            return CreateFeatureResult.invalid_data(
                ["assignment must look like name=value"]
            )
        try:
            value: float | None = float(raw)
            text: str | None = None
        except ValueError:
            value, text = None, raw.strip()
        today = self.clock.today()
        if request.date is None:
            day = today
        else:
            try:
                day = parse_cli_date(request.date, today)
            except ValueError:
                return CreateFeatureResult.invalid_data(
                    ["dates must be ISO dates, now, or durations such as 7d"]
                )
        try:
            listings = self.tickers.list_tickers_by_symbol(symbol)
        except Exception as error:
            return CreateFeatureResult.error([f"Failed to resolve symbol: {error}"])
        if not listings:
            return CreateFeatureResult.not_found([f"unknown symbol {symbol!r}"])
        if len({ticker.exchange for ticker in listings}) > 1:
            return CreateFeatureResult.invalid_data(
                [f"symbol {symbol!r} lists on multiple exchanges"]
            )
        feature = Feature(
            symbol=symbol,
            exchange=listings[0].exchange,
            feature=name,
            date=day,
            value_num=value,
            value_text=text,
            computed_at=datetime.datetime.now(tz=datetime.UTC),
        )
        try:
            self.features.add_feature(feature)
        except ValueError as error:
            return CreateFeatureResult.invalid_data([str(error)])
        except Exception as error:
            message = str(error)
            if "already exists" in message or "duplicate" in message.lower():
                return CreateFeatureResult.invalid_data([message])
            return CreateFeatureResult.error([f"Failed to store feature: {error}"])
        return CreateFeatureResult.success(feature)
