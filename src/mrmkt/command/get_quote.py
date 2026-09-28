"""Latest stock-quote command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.base import BaseResult, Command
from mrmkt.gateway import Quote


@dataclass(frozen=True)
class GetQuoteRequest:
    symbol: str


@dataclass
class GetQuoteResult(BaseResult[Quote]):
    pass


class GetQuote(Command[GetQuoteRequest, GetQuoteResult]):
    """Return the latest quote for one symbol."""

    def __init__(self, quote_gateway):
        self.quote_gateway = quote_gateway

    def execute(self, request: GetQuoteRequest) -> GetQuoteResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return GetQuoteResult.invalid_data([str(error)])
        try:
            quote = self.quote_gateway.get_latest_quote(symbol)
        except KeyError:
            return GetQuoteResult.not_found([f"no quote for symbol {symbol!r}"])
        except Exception as error:
            return GetQuoteResult.error([f"Failed to get quote: {error}"])
        return GetQuoteResult.success(quote)
