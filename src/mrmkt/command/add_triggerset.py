"""Stored trigger-set add command."""

from mrmkt.repo.trigger_sets import TriggerSetNotFound


class UnknownTriggerSetError(ValueError):
    """Raised when adding a trigger to a set that does not exist."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"no trigger set with name {name!r}")


class AddTriggerToSet:
    """Add a trigger to a set; raises ValueError for invalid membership."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, set_name: str, trigger_name: str) -> None:
        try:
            self.repository.add_to_set(set_name, trigger_name)
        except TriggerSetNotFound as error:
            raise UnknownTriggerSetError(error.name) from error
