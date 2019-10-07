from dataclasses import dataclass


@dataclass
class Ticker:
    ticker: str
    exchange: str
    type: str
