"""Unit tests for trigger repository backend selection.

The resolver takes explicit inputs (no environment reads), so selection
is a pure decision covered directly with the in-memory fake repository.
No mocks, no environment mutation.
"""

from hamcrest import assert_that, equal_to, instance_of, is_

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.ext.api_triggers import ApiTriggerRepository
from mrmkt.provider import (
    ApiTriggerProvider,
    PostgresTriggerProvider,
    resolve_trigger_provider,
)


def test_resolve_selects_api_when_provided():
    api = ApiTriggerRepository("http://api.test")
    local = InMemoryFinancialRepository()
    provider = resolve_trigger_provider(api, local)
    assert_that(provider, instance_of(ApiTriggerProvider))
    assert_that(provider.triggers(), is_(api))


def test_resolve_selects_postgres_otherwise():
    local = InMemoryFinancialRepository()
    provider = resolve_trigger_provider(None, local)
    assert_that(provider, instance_of(PostgresTriggerProvider))
    assert_that(provider.triggers(), is_(local))


def test_postgres_close_delegates_to_release():
    calls = []
    provider = PostgresTriggerProvider(
        InMemoryFinancialRepository(), release=lambda: calls.append("closed")
    )
    provider.close()
    assert_that(calls, equal_to(["closed"]))


def test_postgres_close_defaults_to_noop():
    provider = PostgresTriggerProvider(InMemoryFinancialRepository())
    provider.close()


def test_api_close_is_noop():
    provider = ApiTriggerProvider(ApiTriggerRepository("http://api.test"))
    provider.close()
