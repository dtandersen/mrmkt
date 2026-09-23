from abc import abstractmethod
from typing import Type, List


class App:
    @abstractmethod
    def run(self, args: List[str]):
        pass


class Injector:
    @abstractmethod
    def inject(self, obj):
        pass


class AppRunner:
    def __init__(self, injector: Injector):
        self.injector = injector

    def run(self, main: Type[App], args: List[str]):
        app = main()
        self.injector.inject(app)
        app.run(args)
