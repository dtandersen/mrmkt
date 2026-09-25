"""Stored trigger delete command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trigger import Trigger


@dataclass(frozen=True)
class DeleteTriggerRequest:
    name: str


@dataclass
class DeleteTriggerResult(BaseResult[Trigger]):
    pass


class DeleteTrigger(Command[DeleteTriggerRequest, DeleteTriggerResult]):
    """Delete a stored trigger by name (also removed from any trigger sets)."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: DeleteTriggerRequest) -> DeleteTriggerResult:
        try:
            trigger = next(
                (
                    item
                    for item in self.repository.list_triggers()
                    if item.name == request.name
                ),
                None,
            )
        except Exception as error:
            return DeleteTriggerResult.error([f"Failed to remove trigger: {error}"])
        if trigger is None or trigger.id is None:
            return DeleteTriggerResult.not_found(
                [f"no trigger with name {request.name!r}"]
            )
        self.repository.remove_trigger(trigger.id)
        return DeleteTriggerResult.success(trigger)
