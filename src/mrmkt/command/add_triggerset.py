"""Stored trigger-set add command."""

from dataclasses import dataclass, field

from mrmkt.command.base import BaseResult, Command, Status
from mrmkt.repo.trigger_sets import TriggerSetNotFound


@dataclass(frozen=True)
class FieldError:
    """One operator-facing reason a request field was rejected."""

    field: str
    message: str


@dataclass(frozen=True)
class AddTriggerToSetRequest:
    set_name: str
    trigger_name: str


@dataclass
class AddTriggerToSetResult(BaseResult[None]):
    field_errors: list[FieldError] = field(default_factory=list)


class AddTriggerToSet(Command[AddTriggerToSetRequest, AddTriggerToSetResult]):
    """Add a trigger to a set, validating both names before writing."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: AddTriggerToSetRequest) -> AddTriggerToSetResult:
        errors: list[FieldError] = []
        if not self._known_set(request.set_name):
            errors.append(
                FieldError("triggerset", f"Triggerset {request.set_name!r} not found")
            )
        if not self._known_trigger(request.trigger_name):
            errors.append(
                FieldError("trigger", f"Trigger {request.trigger_name!r} not found")
            )
        if errors:
            return AddTriggerToSetResult(
                status=Status.NOT_FOUND,
                errors=[f"{error.field}: {error.message}" for error in errors],
                field_errors=errors,
            )
        self.repository.add_to_set(request.set_name, request.trigger_name)
        return AddTriggerToSetResult.success(None)

    def _known_set(self, name: str) -> bool:
        try:
            self.repository.list_set_members(name)
        except TriggerSetNotFound:
            return False
        return True

    def _known_trigger(self, name: str) -> bool:
        return any(trigger.name == name for trigger in self.repository.list_triggers())
