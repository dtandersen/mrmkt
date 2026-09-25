"""Stored trigger list command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trigger import Trigger


@dataclass(frozen=True)
class ListTriggersRequest:
    enabled_only: bool = False


@dataclass
class ListTriggersResult(BaseResult[list[Trigger]]):
    pass


class ListTriggers(Command[ListTriggersRequest, ListTriggersResult]):
    """List stored triggers, optionally enabled only."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: ListTriggersRequest) -> ListTriggersResult:
        try:
            triggers = self.repository.list_triggers(enabled_only=request.enabled_only)
        except Exception as error:
            return ListTriggersResult.error([f"Failed to list triggers: {error}"])
        return ListTriggersResult.success(triggers)
