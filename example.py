import psycopg2

from common.sql import InsecureSqlGenerator
from common.sqlfinrepo import SqlFinancialRepository
from ext.postgres import PostgresSqlClient
from usecase.runmodel import RunModel
from ext.fmp import FMPReadOnlyFinancialRepository, FmpClient
# logging.basicConfig(level=logging.DEBUG)
# api = FmpApi()
# fin_gtwy = FMPFinancialGateway(api)
cnv = InsecureSqlGenerator()
pool = psycopg2.pool.SimpleConnectionPool(1, 20, user="postgres",
                                          password="local",
                                          host="127.0.0.1",
                                          port="5432",
                                          database="mrmkt")
sql = PostgresSqlClient(cnv, pool)
pg = SqlFinancialRepository(sql)
# f = TestMrMktUseCaseFactory(fin_gtwy, pg)
# injector = UseCaseFactoryInjector(f)
symbol = 'ENPH'
# fmp = FMPFinancialGateway(FmpApi())
# db =
# bal = fmp.balance_sheet(symbol)
# inc = fmp.income_statement(symbol)
buf = RunModel(pg)
buf.analyze(symbol)
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
