"""Read-only price catalog web fragments."""

from litestar import Controller, Response, get

from mrmkt.command.list_prices import ListPricesRequest
from mrmkt.composition import AppContext
from mrmkt.web.results import respond


class PricesController(Controller):
    path = "/fragments/prices"

    @get(sync_to_thread=True)
    def prices(
        self,
        app_context: AppContext,
        symbols: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Response[str]:
        """Render stored daily bars as an HTML table fragment.

        ``symbols`` is a comma-separated list; an empty selection lists
        nothing rather than failing.
        """
        selected = (
            [part.strip() for part in symbols.split(",") if part.strip()]
            if symbols
            else []
        )
        result = app_context.command_factory.list_prices().execute(
            ListPricesRequest(symbols=selected, from_date=from_date, to_date=to_date)
        )
        return respond(
            result, "fragments/prices.html", lambda prices: {"prices": prices}
        )
