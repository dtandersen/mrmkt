"""Stored trigger-set add command."""

from dataclasses import dataclass

from mrmkt.repo.trigger_sets import TriggerSetNotFound


@dataclass(frozen=True)
class FieldError:
    """One operator-facing reason a request field was rejected."""

    field: str
    message: str


class AddTriggerToSetError(ValueError):
    """Raised when an add is invalid; carries every error found.

    Messages are operator-facing: callers print them verbatim.
    """

    def __init__(self, errors: list[FieldError]) -> None:
        self.errors = list(errors)
        super().__init__("\n".join(f"{e.field}: {e.message}" for e in self.errors))


class AddTriggerToSet:
    """Add a trigger to a set, validating both names before writing."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, set_name: str, trigger_name: str) -> None:
        errors: list[FieldError] = []
        if not self._known_set(set_name):
            errors.append(
                FieldError("triggerset", f"Triggerset {set_name!r} not found")
            )
        if not self._known_trigger(trigger_name):
            errors.append(FieldError("trigger", f"Trigger {trigger_name!r} not found"))
        if errors:
            raise AddTriggerToSetError(errors)
        self.repository.add_to_set(set_name, trigger_name)

    def _known_set(self, name: str) -> bool:
        try:
            self.repository.list_set_members(name)
        except TriggerSetNotFound:
            return False
        return True

    def _known_trigger(self, name: str) -> bool:
        return any(trigger.name == name for trigger in self.repository.list_triggers())
