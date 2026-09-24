"""Stored trigger-set create command."""

from mrmkt.command.triggersets_common import _default_set_name


class CreateTriggerSet:
    """Create an empty trigger set; returns its name."""

    def __init__(self, repository, name_generator=_default_set_name):
        self.repository = repository
        self.name_generator = name_generator

    def execute(self, name: str | None) -> str:
        set_name = name.strip() if name and name.strip() else self.name_generator()
        return self.repository.create_set(set_name)
