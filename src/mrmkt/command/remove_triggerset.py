"""Stored trigger-set remove command."""


class RemoveTriggerFromSet:
    """Remove a trigger from a set; raises ValueError when not a member."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, set_name: str, trigger_name: str) -> None:
        if not self.repository.remove_from_set(set_name, trigger_name):
            raise ValueError(f"no trigger {trigger_name!r} in trigger set {set_name!r}")
