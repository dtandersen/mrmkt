"""Stored trigger show command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trigger import Trigger


@dataclass(frozen=True)
class ShowTriggerRequest:
    name: str


@dataclass
class ShowTriggerResult(BaseResult[Trigger]):
    pass


class ShowTrigger(Command[ShowTriggerRequest, ShowTriggerResult]):
    """Return a single stored trigger by name."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: ShowTriggerRequest) -> ShowTriggerResult:
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
            return ShowTriggerResult.error([f"Failed to show trigger: {error}"])
        if trigger is None:
            return ShowTriggerResult.not_found(
                [f"no trigger with name {request.name!r}"]
            )
        return ShowTriggerResult.success(trigger)
