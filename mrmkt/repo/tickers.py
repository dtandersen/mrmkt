from abc import ABC, abstractmethod
from typing import List


class ReadOnlyTickerRepository(ABC):
    @abstractmethod
    def get_symbols(self) -> List[str]:
        pass
