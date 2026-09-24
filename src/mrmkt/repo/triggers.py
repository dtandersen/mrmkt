from abc import ABC, abstractmethod

from mrmkt.entity.trigger import Trigger


class TriggerRepository(ABC):
    @abstractmethod
    def list_triggers(self, enabled_only: bool = False) -> list[Trigger]:
        pass

    @abstractmethod
    def add_trigger(self, trigger: Trigger) -> Trigger:
        pass

    @abstractmethod
    def remove_trigger(self, trigger_id: int) -> bool:
        pass

    @abstractmethod
    def set_trigger_enabled(self, trigger_id: int, enabled: bool) -> bool:
        pass
