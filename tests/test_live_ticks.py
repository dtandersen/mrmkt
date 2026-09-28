"""Live ticks over the RabbitMQ bus (no Tiingo, no broker)."""

import asyncio
from datetime import UTC, datetime

from hamcrest import assert_that, contains_string, equal_to
from tests.fakes import CapturingLog, FakeMessageQueue

from mrmkt.command.start_engine import DEFAULT_SUBJECT
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.ext.backend import InMemoryBackend
from mrmkt.gateway import PriceProvider, Quote


def _quote(symbol="AAA"):
    return Quote(
        symbol=symbol,
        bid=106.0,
        ask=107.0,
        timestamp=datetime(2026, 9, 28, 14, 0, tzinfo=UTC),
    )


def _session(queue=None, **kwargs):
    return cli_dependencies_for_testing(
        repository=InMemoryBackend(), engine_queue=queue, **kwargs
    )


def test_live_ticks_attaches_to_bus_subject_and_yields_quotes():
    queue = FakeMessageQueue()
    factory = _session(queue).command_factory

    async def collect():
        agen = factory.live_ticks("AAA")
        pending = asyncio.ensure_future(agen.__anext__())
        for _ in range(500):
            if queue.subjects:
                break
            await asyncio.sleep(0.01)
        queue.deliver(f"{DEFAULT_SUBJECT}.AAA", _quote())
        try:
            return await asyncio.wait_for(pending, timeout=5)
        finally:
            await agen.aclose()

    assert_that(asyncio.run(collect()), equal_to(_quote()))
    assert_that(queue.subjects, equal_to([f"{DEFAULT_SUBJECT}.AAA"]))


class _DeadProvider(PriceProvider):
    def subscribe(self, symbols, *, on_quote) -> None:
        raise ConnectionError("broker down")

    def close(self) -> None:
        pass


def test_live_ticks_logs_instead_of_crash_on_dead_bus():
    log = CapturingLog()
    factory = cli_dependencies_for_testing(
        repository=InMemoryBackend(), engine_prices=_DeadProvider(), log=log
    ).command_factory

    async def collect():
        agen = factory.live_ticks("AAA")
        try:
            await asyncio.wait_for(agen.__anext__(), timeout=2)
        except TimeoutError:
            return "no-quotes"
        finally:
            await agen.aclose()

    assert_that(asyncio.run(collect()), equal_to("no-quotes"))
    assert_that(" ".join(log.lines), contains_string("live prices unavailable for AAA"))
