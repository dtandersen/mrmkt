"""Shared building blocks for commands."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Self


class Status(Enum):
    # Represents the status of a command execution result.
    # SUCCESS: The command executed successfully.
    SUCCESS = 1

    # NOT_FOUND: The requested resource was not found.
    NOT_FOUND = 2

    # INVALID_DATA: The provided data was invalid or did not meet the required criteria.
    INVALID_DATA = 3

    # ERROR: An unexpected error occurred during command execution.
    ERROR = 4


@dataclass
class BaseResult[T](ABC):
    status: Status
    errors: list[str] = field(default_factory=list)
    result: T | None = None

    @classmethod
    def success(cls, result: T) -> Self:
        return cls(status=Status.SUCCESS, result=result)

    @classmethod
    def not_found(cls, errors: list[str] | None = None) -> Self:
        return cls(status=Status.NOT_FOUND, errors=errors or [])

    @classmethod
    def invalid_data(cls, errors: list[str] | None = None) -> Self:
        return cls(status=Status.INVALID_DATA, errors=errors or [])

    @classmethod
    def error(cls, errors: list[str] | None = None) -> Self:
        return cls(status=Status.ERROR, errors=errors or [])

    def is_success(self) -> bool:
        return self.status == Status.SUCCESS

    def is_not_found(self) -> bool:
        return self.status == Status.NOT_FOUND

    def is_invalid_data(self) -> bool:
        return self.status == Status.INVALID_DATA

    def is_error(self) -> bool:
        return self.status == Status.ERROR


class Command[REQ, RES: BaseResult](ABC):
    @abstractmethod
    def execute(self, request: REQ) -> RES:
        pass
