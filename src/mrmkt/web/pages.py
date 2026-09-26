"""Shell pages for the read-only web view."""

from litestar import Controller, MediaType, Response, get

from mrmkt.web.results import render


class PagesController(Controller):
    path = "/"

    @get(sync_to_thread=False)
    def index(self) -> Response[str]:
        """Render the shell page; sections load via HTMX fragment requests."""
        return Response(render("index.html"), media_type=MediaType.HTML)
