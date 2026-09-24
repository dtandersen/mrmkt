from abc import ABC, abstractmethod


class TriggerSetRepository(ABC):
    """Named sets of triggers, keyed by name throughout."""

    @abstractmethod
    def create_set(self, name: str) -> str:
        """Create an empty set; returns its name."""
        pass

    @abstractmethod
    def add_to_set(self, set_name: str, trigger_name: str) -> None:
        """Add a trigger to a set; adding a member twice is a no-op."""
        pass

    @abstractmethod
    def remove_from_set(self, set_name: str, trigger_name: str) -> bool:
        """Remove a trigger from a set; False when set or member is missing."""
        pass

    @abstractmethod
    def list_set_members(self, set_name: str) -> list[str]:
        """Sorted member trigger names; raises ValueError for an unknown set."""
        pass
