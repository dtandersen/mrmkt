"""Stored trigger enable/disable command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trigger import Trigger


@dataclass(frozen=True)
class SetTriggerEnabledRequest:
    trigger_id: int
    enabled: bool


@dataclass
class SetTriggerEnabledResult(BaseResult[Trigger]):
    pass


class SetTriggerEnabled(Command[SetTriggerEnabledRequest, SetTriggerEnabledResult]):
    """Enable or disable a stored trigger by id."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: SetTriggerEnabledRequest) -> SetTriggerEnabledResult:
        try:
            matches = [
                item
                for item in self.repository.list_triggers()
                if item.id == request.trigger_id
            ]
        except Exception as error:
            return SetTriggerEnabledResult.error([f"Failed to update trigger: {error}"])
        if not matches:
            return SetTriggerEnabledResult.not_found(
                [f"no trigger with id {request.trigger_id}"]
            )
        try:
            updated = self.repository.set_trigger_enabled(
                request.trigger_id, request.enabled
            )
        except Exception as error:
            return SetTriggerEnabledResult.error([f"Failed to update trigger: {error}"])
        if not updated:
            return SetTriggerEnabledResult.not_found(
                [f"no trigger with id {request.trigger_id}"]
            )
        try:
            refreshed = next(
                item
                for item in self.repository.list_triggers()
                if item.id == request.trigger_id
            )
        except Exception as error:
            return SetTriggerEnabledResult.error([f"Failed to update trigger: {error}"])
        return SetTriggerEnabledResult.success(refreshed)
