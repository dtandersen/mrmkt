"""Moneyman-owned verification for the alerts handoff (user-requested pytest).

Covers the exact behaviors I verified manually against the live tree:
1. ``LevelsUseCase`` (the ``mrmkt ranges`` backend) selection semantics — explicit symbols never expand to
   the whole catalog (regression guard for the bug manager caught), and
   empty selection returns nothing.
2. ``dry_run_alerts`` (the ``mrmkt watch --dry-run`` backend) causality — replays stored lows against prior-close
   levels, fires only at/below the level, and touches no sink (delivery is
   the engine's ``on_alert`` callback only).

Self-contained: uses ``InMemoryFinancialRepository`` and synthetic bars, so
it never touches Postgres, the network, or any real sink. Owned by the
moneyman session; manager/worker may relocate or delete on request.
"""

from datetime import date, timedelta

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.alerts import AlertEngine, LevelsUseCase, dry_run_alerts

START = date(2026, 1, 5)  # a Monday


def business_days(start: date, n: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def add_flat_series(
    repo: InMemoryFinancialRepository,
    symbol: str,
    n: int,
    price: float,
    low_factor: float = 0.995,
    tag: str | None = None,
    drift: float = 0.0,
) -> None:
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    if tag is not None:
        repo.add_tag(symbol, "NASDAQ", tag)
    level_price = price
    for day in business_days(START, n):
        level_price *= 1 + drift
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=level_price,
                high=level_price * 1.005,
                low=level_price * low_factor,
                close=level_price,
                volume=1_000_000.0,
            )
        )


def test_levels_explicit_symbols_never_expand_to_catalog():
    repo = InMemoryFinancialRepository()
    for symbol in ("AAA", "BBB", "CCC"):
        add_flat_series(repo, symbol, 60, 100.0)
    use_case = LevelsUseCase(repo)
    as_of = business_days(START, 60)[-1]

    only_aaa = use_case.execute(include_tags=[], symbols=["AAA"], as_of=as_of)
    assert [row.symbol for row in only_aaa.rows] == ["AAA"]

    empty = use_case.execute(include_tags=[], symbols=[], as_of=as_of)
    assert empty.rows == []


def test_levels_tag_selection_stays_within_tags():
    repo = InMemoryFinancialRepository()
    add_flat_series(repo, "AAA", 60, 100.0, tag="idx")
    add_flat_series(repo, "BBB", 60, 100.0, tag="idx")
    add_flat_series(repo, "CCC", 60, 200.0)  # untagged: must never appear
    use_case = LevelsUseCase(repo)
    as_of = business_days(START, 60)[-1]

    result = use_case.execute(include_tags=["idx"], symbols=[], as_of=as_of)
    assert sorted(row.symbol for row in result.rows) == ["AAA", "BBB"]


def test_dry_run_fires_only_at_or_below_level_with_no_sink():
    repo = InMemoryFinancialRepository()
    # Gentle drift keeps the seed close above its range low so the rule arms.
    add_flat_series(repo, "DIP", 40, 100.0, drift=0.005)
    # A dramatic one-day dip below any plausible range low, then recovery.
    dip_day = business_days(START, 41)[-1]
    repo.add_price(
        StockPrice(
            symbol="DIP",
            date=dip_day,
            open=100.0,
            high=100.5,
            low=50.0,
            close=99.0,
            volume=5_000_000.0,
        )
    )
    bars = {"DIP": repo.list_prices("DIP")}

    delivered: list = []
    engine = AlertEngine(on_alert=delivered.append)
    fired = dry_run_alerts(engine, bars)

    assert fired, "expected the engineered dip to trigger an alert"
    assert delivered == fired, "dry run must deliver only via on_alert (no sinks)"
    for alert in fired:
        assert alert.symbol == "DIP"
        assert alert.price <= alert.level
        assert alert.session == "regular"
