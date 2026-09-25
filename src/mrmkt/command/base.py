"""Shared building blocks for commands."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BaseResult:
    success: bool
    errors: list[str] = field(default_factory=list)


class Command[REQ, RES: BaseResult](ABC):
    @abstractmethod
    def execute(self, request: REQ) -> RES:
        pass
