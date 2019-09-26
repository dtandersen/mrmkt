import mrmkt


repo = mrmkt.ext.postgresx()
print(repo.list_prices("SPY"))
