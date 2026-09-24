"""Stored trigger show command."""

from mrmkt.entity.trigger import Trigger


class ShowTrigger:
    """Return a single stored trigger by name; raises ValueError when missing."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, name: str) -> Trigger:
        trigger = next((t for t in self.repository.list_triggers() if t.name == name), None)
        if trigger is None:
            raise ValueError(f"no trigger with name {name!r}")
        return trigger
