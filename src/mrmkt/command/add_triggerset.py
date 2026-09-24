"""Stored trigger-set add command."""


class AddTriggerToSet:
    """Add a trigger to a set; raises ValueError for unknown set/trigger."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, set_name: str, trigger_name: str) -> None:
        self.repository.add_to_set(set_name, trigger_name)
