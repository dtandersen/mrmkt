from dataclasses import dataclass


@dataclass
class IncomeStatement:
    symbol: str
    date: str
    netIncome: float
    waso: int
