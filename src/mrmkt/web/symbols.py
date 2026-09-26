"""Read-only symbol catalog web fragments."""

from typing import cast

from litestar import Controller, Response, get

from mrmkt.command.list_symbols import ListSymbolsRequest
from mrmkt.composition import AppContext
from mrmkt.entity.ticker import Ticker
from mrmkt.web.results import respond, status_code_of


class SymbolsController(Controller):
    path = "/fragments/symbols"

    @get(sync_to_thread=True)
    def symbols(self, app_context: AppContext, tag: str | None = None) -> Response[str]:
        """Render stored symbols as an HTML table fragment."""
        result = app_context.command_factory.list_symbols().execute(
            ListSymbolsRequest(tag=tag)
        )
        return respond(
            result, "fragments/symbols.html", lambda tickers: {"tickers": tickers}
        )

    @get("/lookup", sync_to_thread=True)
    def lookup(self, app_context: AppContext) -> list[dict] | Response[dict]:
        """Return stored symbols as JSON for the chart symbol lookup."""
        result = app_context.command_factory.list_symbols().execute(
            ListSymbolsRequest(tag=None)
        )
        if result.is_success():
            tickers = cast(list[Ticker], result.result)
            return [
                {
                    "ticker": ticker.ticker,
                    "exchange": ticker.exchange,
                    "type": ticker.type,
                }
                for ticker in tickers
            ]
        return Response(
            content={"errors": result.errors},
            status_code=status_code_of(result),
        )
