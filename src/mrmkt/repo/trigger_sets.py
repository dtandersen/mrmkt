from abc import ABC, abstractmethod


class TriggerSetNotFound(ValueError):
    """Raised when a requested trigger set does not exist."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"no trigger set with name {name!r}")


class TriggerSetRepository(ABC):
    """Named sets of triggers, keyed by name throughout."""

    @abstractmethod
    def create_set(self, name: str) -> str:
        """Create an empty set; returns its name."""
        ...

    @abstractmethod
    def add_to_set(self, set_name: str, trigger_name: str) -> None:
        """Add a trigger to a set; adding a member twice is a no-op."""
        ...

    @abstractmethod
    def remove_from_set(self, set_name: str, trigger_name: str) -> bool:
        """Remove a trigger from a set; False when set or member is missing."""
        ...

    @abstractmethod
    def list_set_members(self, set_name: str) -> list[str]:
        """Sorted member trigger names; raises TriggerSetNotFound if absent."""
        ...
