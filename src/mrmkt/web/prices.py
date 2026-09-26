"""Read-only price catalog web fragments."""

from typing import cast

from litestar import Controller, Response, get

from mrmkt.command.list_prices import ListPricesRequest
from mrmkt.composition import AppContext
from mrmkt.entity.stock_price import StockPrice
from mrmkt.web.results import respond, status_code_of


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

    @get("/chart", sync_to_thread=True)
    def chart_data(
        self,
        app_context: AppContext,
        symbols: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict] | Response[dict]:
        """Return stored daily bars as JSON for the chart widget.

        ``symbols`` is a comma-separated list; an empty selection yields
        an empty series rather than failing. Each bar carries a ``time``
        field (ISO date) shaped for Lightweight Charts.
        """
        selected = (
            [part.strip() for part in symbols.split(",") if part.strip()]
            if symbols
            else []
        )
        result = app_context.command_factory.list_prices().execute(
            ListPricesRequest(symbols=selected, from_date=from_date, to_date=to_date)
        )
        if result.is_success():
            prices = cast(list[StockPrice], result.result)
            return [
                {
                    "symbol": price.symbol,
                    "time": price.date.isoformat(),
                    "open": price.open,
                    "high": price.high,
                    "low": price.low,
                    "close": price.close,
                    "volume": price.volume,
                }
                for price in prices
            ]
        return Response(
            content={"errors": result.errors},
            status_code=status_code_of(result),
        )
