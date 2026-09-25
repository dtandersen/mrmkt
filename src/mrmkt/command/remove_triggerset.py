"""Stored trigger-set remove command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command


@dataclass(frozen=True)
class RemoveTriggerFromSetRequest:
    set_name: str
    trigger_name: str


@dataclass
class RemoveTriggerFromSetResult(BaseResult[None]):
    pass


class RemoveTriggerFromSet(
    Command[RemoveTriggerFromSetRequest, RemoveTriggerFromSetResult]
):
    """Remove a trigger from a set."""

    def __init__(self, repository):
        self.repository = repository

    def execute(
        self, request: RemoveTriggerFromSetRequest
    ) -> RemoveTriggerFromSetResult:
        try:
            removed = self.repository.remove_from_set(
                request.set_name, request.trigger_name
            )
        except Exception as error:
            return RemoveTriggerFromSetResult.error(
                [f"Failed to remove trigger from set: {error}"]
            )
        if not removed:
            return RemoveTriggerFromSetResult.not_found(
                [
                    f"no trigger {request.trigger_name!r} "
                    f"in trigger set {request.set_name!r}"
                ]
            )
        return RemoveTriggerFromSetResult.success(None)
