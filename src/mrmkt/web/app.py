"""Litestar application factory for the web view and JSON API."""

from collections.abc import Callable

from litestar import Litestar
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig

from mrmkt.composition import AppContext
from mrmkt.web.api import API_CONTROLLERS
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
            *API_CONTROLLERS,
        ],
        dependencies={
            "app_context": Provide(app_context_provider, sync_to_thread=False)
        },
        openapi_config=OpenAPIConfig(title="mrmkt", version="1.0.0"),
    )
    app.state.api_token = api_token
    return app
