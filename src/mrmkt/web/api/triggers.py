"""JSON trigger endpoints (DTOs in, DTOs out, never entities).

Read/write access to the stored trigger catalog for remote CLI use:
the cluster runs the watcher against Postgres while operators manage
triggers over HTTP. Each endpoint executes a command, mirroring the
CLI handlers; validation and status mapping stay identical.
"""

from litestar import Controller, Response, delete, get, patch, post

from mrmkt.api.trigger_dtos import (
    CreateTriggerDto,
    SetEnabledDto,
    TriggerDto,
    create_request_from_dto,
    trigger_to_dto,
)
from mrmkt.command.delete_trigger import DeleteTriggerRequest
from mrmkt.command.list_trigger import ListTriggersRequest
from mrmkt.command.set_trigger_enabled import SetTriggerEnabledRequest
from mrmkt.composition import AppContext
from mrmkt.web.api.auth import require_api_token
from mrmkt.web.results import status_code_of


class ApiTriggersController(Controller):
    path = "/api/triggers"
    guards = [require_api_token]

    @get(sync_to_thread=True)
    def list_triggers(
        self, app_context: AppContext, enabled_only: bool = False
    ) -> list[TriggerDto] | Response[dict]:
        """List stored triggers as JSON DTOs."""
        result = app_context.command_factory.list_triggers().execute(
            ListTriggersRequest(enabled_only=enabled_only)
        )
        if not result.is_success():
            return Response(
                content={"errors": result.errors},
                status_code=status_code_of(result),
            )
        return [trigger_to_dto(trigger) for trigger in result.result or []]

    @post(status_code=201, sync_to_thread=True)
    def create_trigger(
        self, app_context: AppContext, data: CreateTriggerDto
    ) -> TriggerDto | Response[dict]:
        """Store a trigger; runs the CreateTrigger command remotely."""
        result = app_context.command_factory.create_trigger().execute(
            create_request_from_dto(data)
        )
        if not result.is_success():
            return Response(
                content={"errors": result.errors},
                status_code=status_code_of(result),
            )
        assert result.result is not None
        return trigger_to_dto(result.result)

    @delete("/{trigger_id:int}", status_code=200, sync_to_thread=True)
    def delete_trigger(
        self, app_context: AppContext, trigger_id: int
    ) -> TriggerDto | Response[dict]:
        """Delete a stored trigger by id; 404 when unknown."""
        listed = app_context.command_factory.list_triggers().execute(
            ListTriggersRequest(enabled_only=False)
        )
        if not listed.is_success():
            return Response(
                content={"errors": listed.errors},
                status_code=status_code_of(listed),
            )
        match = next(
            (item for item in listed.result or [] if item.id == trigger_id), None
        )
        if match is None:
            return Response(
                content={"errors": [f"no trigger with id {trigger_id}"]},
                status_code=404,
            )
        result = app_context.command_factory.delete_trigger().execute(
            DeleteTriggerRequest(name=match.name)
        )
        if not result.is_success():
            return Response(
                content={"errors": result.errors},
                status_code=status_code_of(result),
            )
        assert result.result is not None
        return trigger_to_dto(result.result)

    @patch("/{trigger_id:int}", sync_to_thread=True)
    def set_trigger_enabled(
        self, app_context: AppContext, trigger_id: int, data: SetEnabledDto
    ) -> TriggerDto | Response[dict]:
        """Enable or disable a stored trigger by id; 404 when unknown."""
        result = app_context.command_factory.set_trigger_enabled().execute(
            SetTriggerEnabledRequest(trigger_id=trigger_id, enabled=data.enabled)
        )
        if not result.is_success():
            return Response(
                content={"errors": result.errors},
                status_code=status_code_of(result),
            )
        assert result.result is not None
        return trigger_to_dto(result.result)
