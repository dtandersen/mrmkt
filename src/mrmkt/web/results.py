"""Shared mapping from command results to web responses."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

from jinja2 import Environment, FileSystemLoader
from litestar import MediaType, Response

from mrmkt.command.base import BaseResult, Status

_templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=True,
)


def render(template: str, **context) -> str:
    """Render a Jinja template from the web package's template directory."""
    return _templates.get_template(template).render(**context)


_STATUS_CODES = {
    Status.INVALID_DATA: 400,
    Status.NOT_FOUND: 404,
}


def respond[T](
    result: BaseResult[T], template: str, context_of: Callable[[T], dict]
) -> Response[str]:
    """Render a successful payload, or an error fragment with status."""
    if result.is_success():
        return Response(
            render(template, **context_of(cast(T, result.result))),
            media_type=MediaType.HTML,
            status_code=200,
        )
    return Response(
        render("fragments/error.html", errors=result.errors),
        media_type=MediaType.HTML,
        status_code=_STATUS_CODES.get(result.status, 500),
    )
