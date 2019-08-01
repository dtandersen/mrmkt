from buffet import Buffet
from fmp import FMPFinancialGateway

symbol = 'AAPL'
fmp = FMPFinancialGateway()
bal = fmp.getBalanceSheet(symbol)
inc = fmp.getIncomeStatement(symbol)
buf = Buffet()
x = buf.analyze(inc, bal)
print(f'equity={x.equity}')
print(f'book value={x.bookValue}')
print(f'eps={x.eps}')
print(f'pe={x.pe}')