import copy
from dataclasses import dataclass
from typing import Generic, TypeVar, Iterable, Callable

from common.sql import Duplicate

T = TypeVar('T')


@dataclass
class Table(Generic[T]):
    values: dict

    def __init__(self, keygenerator: Callable[[T], str]):
        self.values = {}
        self.keygen = keygenerator

    def all(self) -> Iterable[T]:
        return copy.copy(list(self.values.values()))

    def add(self, value):
        try:
            self.values[self.keygen(value)] = copy.copy(value)
        except KeyError:
            raise Duplicate

    def size(self):
        return len(self.values)

    def get(self, key: str):
        return copy.copy(self.values[key])

    def pop(self, key: str):
        try:
            self.values.pop(key)
        except KeyError:
            pass

    def filter(self, predicate: Callable):
        return list(filter(predicate, self.all()))

