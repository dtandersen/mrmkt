"""Litestar application factory for the web view and JSON API."""

from collections.abc import Callable

from litestar import Litestar
from litestar.di import Provide

from mrmkt.composition import AppContext
from mrmkt.web.api import ApiTriggersController
from mrmkt.web.pages import PagesController
from mrmkt.web.prices import PricesController
from mrmkt.web.symbols import SymbolsController
from mrmkt.web.triggers import TriggersController


def create_web_app(
    app_context_provider: Callable[[], AppContext],
    api_token: str | None = None,
) -> Litestar:
    """Build the web app; dependencies resolve per request for testability.

    ``api_token`` guards ``/api/*`` with a bearer token; ``None`` leaves
    the API open (local development only).
    """
    app = Litestar(
        [
            PagesController,
            SymbolsController,
            PricesController,
            TriggersController,
            ApiTriggersController,
        ],
        dependencies={
            "app_context": Provide(app_context_provider, sync_to_thread=False)
        },
    )
    app.state.api_token = api_token
    return app
