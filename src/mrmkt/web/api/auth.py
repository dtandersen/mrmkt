"""Shared bearer-token guard for the JSON API.

The expected token lives on ``app.state.api_token`` (wired from the
``MRMKT_API_TOKEN`` environment variable by the server entrypoints).
When no token is configured the API stays open for local development;
when one is configured every ``/api/*`` request needs
``Authorization: Bearer <token>``. The token value itself never appears
in responses, logs, or error messages.
"""

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler


def api_token_from_env() -> str | None:
    """Read the API bearer token config (never logged or echoed)."""
    import os

    return os.environ.get("MRMKT_API_TOKEN") or None


def require_api_token(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Enforce the configured API token, if any."""
    expected = connection.app.state.api_token
    if not expected:
        return
    presented = connection.headers.get("authorization", "")
    if presented != f"Bearer {expected}":
        raise NotAuthorizedException("invalid or missing API token")
