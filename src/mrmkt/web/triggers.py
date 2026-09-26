"""Read-only trigger catalog web fragments."""

from litestar import Controller, Response, get

from mrmkt.command.list_trigger import ListTriggersRequest
from mrmkt.composition import AppContext
from mrmkt.web.results import respond


class TriggersController(Controller):
    path = "/fragments/triggers"

    @get(sync_to_thread=True)
    def triggers(
        self, app_context: AppContext, enabled_only: bool = False
    ) -> Response[str]:
        """Render stored triggers as an HTML table fragment."""
        result = app_context.command_factory.list_triggers().execute(
            ListTriggersRequest(enabled_only=enabled_only)
        )
        return respond(
            result, "fragments/triggers.html", lambda triggers: {"triggers": triggers}
        )
