"""Stored trigger delete command."""

from mrmkt.entity.trigger import Trigger


class DeleteTrigger:
    """Delete a stored trigger by name (also removed from any trigger sets)."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, name: str) -> Trigger:
        """Delete the trigger; returns it, raises ValueError when missing."""
        trigger = next((t for t in self.repository.list_triggers() if t.name == name), None)
        if trigger is None or trigger.id is None:
            raise ValueError(f"no trigger with name {name!r}")
        self.repository.remove_trigger(trigger.id)
        return trigger
