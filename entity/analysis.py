from dataclasses import dataclass


@dataclass
class Analysis():
    netIncome: float
    buffetNumber: float
    priceToBookValue: float
    date: str
    symbol: str
    sharesOutstanding: float
    liabilities: float
    assets: float
    marginOfSafety: float
    bookValue: float
    eps: float
    equity: float
    pe: float
