# Orders

Paper-account orders (Alpaca paper endpoint only).

## Create an order

Submit a GTC limit order. The resting limit fills only on the touch —
never a chase. With `--stop`, the order carries an OTO stop-loss leg.

```
mrmkt order create <symbol> --buy <qty> --price <float> [--stop <float>] [--expire <date>]
mrmkt order create <symbol> --sell <qty> --price <float> [--stop <float>]
```

## List orders

List orders as deterministic CSV (default: open only).

mrmkt order list [--status open|closed|all]

## Show an order

Show a single order as CSV.

mrmkt order show <order-id>

## Cancel an order

Cancel an open order.

mrmkt order cancel <order-id>
