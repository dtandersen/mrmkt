"""Litestar application factory for the read-only web view."""

from collections.abc import Callable

from litestar import Litestar
from litestar.di import Provide

from mrmkt.composition import AppContext
from mrmkt.web.pages import PagesController
from mrmkt.web.prices import PricesController
from mrmkt.web.symbols import SymbolsController
from mrmkt.web.triggers import TriggersController


def create_web_app(
    app_context_provider: Callable[[], AppContext],
) -> Litestar:
    """Build the web app; dependencies resolve per request for testability."""
    return Litestar(
        [PagesController, SymbolsController, PricesController, TriggersController],
        dependencies={
            "app_context": Provide(app_context_provider, sync_to_thread=False)
        },
    )
