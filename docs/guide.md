# Import the prices

To have prices you need to import them first.

```shell
mrmkt prices import --provider alpaca --tag sp500 --from 5y
mrmkt prices import --provider alpaca AAPL --from 5y
mrmkt prices import --provider alpaca --tag sp500 --tag russell2000 --from 7d
```

Yahoo Finance imports use its unofficial chart API and may be rate-limited. The
local symbol `VIX` maps to Yahoo's index symbol `^VIX`:

```shell
mrmkt prices import --provider yahoo VIX --from 2026-09-25 --to 2026-09-25
```
