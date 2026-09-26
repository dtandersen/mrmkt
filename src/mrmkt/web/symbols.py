"""Read-only symbol catalog web fragments."""

from litestar import Controller, Response, get

from mrmkt.command.list_symbols import ListSymbolsRequest
from mrmkt.composition import AppContext
from mrmkt.web.results import respond


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
