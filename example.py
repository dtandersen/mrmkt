from buffet import Buffet
from fingtwy import FMPFinancialGateway

symbol = 'alb'
fmp = FMPFinancialGateway()
bal = fmp.balance_sheet(symbol)
inc = fmp.income_statement(symbol)
buf = Buffet(fmp)
x = buf.analyze(inc)
print(f'  symbol={x.symbol}')
print(f'  date={x.date}')
print(f'  assets={x.assets}')
print(f'- liabilities={x.liabilities}')
print("---------------")
print(f'  equity={x.equity}')
print(f'  marginOfSafety={x.marginOfSafety * 100}%')
print(f'  net income={x.netIncome}')
print(f'  shares outstanding={x.sharesOutstanding}')
print(f'  book value={x.bookValue}')
print(f'  eps={x.eps}')
print(f'  P/E={x.pe}')
print(f'  P/BV={x.priceToBookValue}')
print(f'  Buffet={x.buffetNumber}')
