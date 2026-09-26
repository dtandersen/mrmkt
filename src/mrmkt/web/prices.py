"""Read-only price catalog web fragments."""

import asyncio
import json
from typing import cast

from litestar import Controller, Response, get
from litestar.response import ServerSentEvent, ServerSentEventMessage

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

    @get("/live", sync_to_thread=False)
    async def live(
        self, app_context: AppContext, symbol: str = "NVDA"
    ) -> ServerSentEvent | Response[dict]:
        """Stream live trade ticks as JSON Server-Sent Events.

        The first event carries the latest stored close (or a bare
        heartbeat when nothing is stored) so charts learn it instantly,
        including when the market is closed and no ticks flow.
        """
        selected = symbol.strip().upper() if symbol and symbol.strip() else "NVDA"
        result = app_context.command_factory.list_prices().execute(
            ListPricesRequest(symbols=[selected])
        )
        if result.is_success():
            ticks = cast(list[StockPrice], result.result)
            baseline = ticks[-1] if ticks else None
            return ServerSentEvent(
                content=self._live_events(app_context, selected, baseline),
                event_type="tick",
            )
        return Response(
            content={"errors": result.errors},
            status_code=status_code_of(result),
        )

    async def _live_events(self, app_context, symbol, baseline):
        """Yield pill HTML, then live ticks; comment keepalives between ticks."""
        from mrmkt.common.clock import ET

        if baseline is None:
            yield json.dumps({"symbol": symbol, "live": False})
        else:
            yield json.dumps(
                {
                    "symbol": symbol,
                    "close": baseline.close,
                    "date": baseline.date.isoformat(),
                    "live": False,
                }
            )
        ticks = app_context.command_factory.live_ticks(symbol)
        iterator = ticks.__aiter__()
        while True:
            try:
                tick = await asyncio.wait_for(iterator.__anext__(), timeout=20)
            except StopAsyncIteration:
                return
            except TimeoutError:
                yield ServerSentEventMessage(comment="ping")
                continue
            yield json.dumps(
                {
                    "symbol": tick.symbol,
                    "price": tick.price,
                    "date": tick.at.astimezone(ET).date().isoformat(),
                    "time": tick.at.astimezone(ET).strftime("%H:%M:%S"),
                    "live": True,
                }
            )
