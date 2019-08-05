class IncomeStatement:
    def __init__(self, symbol='', date='', netIncome=0, waso=0):
        self.date = date
        self.waso = waso
        self.netIncome = netIncome
        self.symbol = symbol
