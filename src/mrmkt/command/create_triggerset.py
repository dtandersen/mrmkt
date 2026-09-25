"""Stored trigger-set create command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.triggersets_common import _default_set_name


@dataclass(frozen=True)
class CreateTriggerSetRequest:
    name: str | None = None


@dataclass
class CreateTriggerSetResult(BaseResult[str]):
    pass


class CreateTriggerSet(Command[CreateTriggerSetRequest, CreateTriggerSetResult]):
    """Create an empty trigger set; returns its name."""

    def __init__(self, repository, name_generator=_default_set_name):
        self.repository = repository
        self.name_generator = name_generator

    def execute(self, request: CreateTriggerSetRequest) -> CreateTriggerSetResult:
        name = request.name
        set_name = name.strip() if name and name.strip() else self.name_generator()
        try:
            stored = self.repository.create_set(set_name)
        except ValueError as error:
            return CreateTriggerSetResult.invalid_data([str(error)])
        except Exception as error:
            return CreateTriggerSetResult.error(
                [f"Failed to create trigger set: {error}"]
            )
        return CreateTriggerSetResult.success(stored)
