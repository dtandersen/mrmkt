"""Stored trigger list command."""

from mrmkt.entity.trigger import Trigger


class ListTriggers:
    """List stored triggers, optionally enabled only."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, enabled_only: bool = False) -> list[Trigger]:
        return self.repository.list_triggers(enabled_only=enabled_only)
