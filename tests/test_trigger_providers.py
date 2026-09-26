"""Unit tests for the trigger ProviderFactory (string in, provider out).

The factory takes explicit inputs (no environment reads), so selection
is covered directly with the in-memory fake repository. No mocks, no
environment mutation.
"""

import secrets

from hamcrest import assert_that, contains_string, equal_to, instance_of, is_
from pytest import raises

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.ext.api_triggers import ApiTriggerRepository
from mrmkt.provider import (
    ApiTriggerProvider,
    PostgresTriggerProvider,
    TriggerProviderFactory,
)

TEST_API_TOKEN = secrets.token_hex(16)


def _factory(local=None, api_url=None, api_token=None):
    return TriggerProviderFactory(
        local_repository=local if local is not None else InMemoryFinancialRepository(),
        api_url=api_url,
        api_token=api_token,
    )


def test_create_postgres_vends_local():
    local = InMemoryFinancialRepository()
    provider = TriggerProviderFactory(local_repository=local).create("postgres")
    assert_that(provider, instance_of(PostgresTriggerProvider))
    assert_that(provider.triggers(), is_(local))


def test_create_api_builds_http_backend():
    provider = _factory(api_url="http://api.test", api_token=TEST_API_TOKEN).create(
        "api"
    )
    assert_that(provider, instance_of(ApiTriggerProvider))
    repository = provider.triggers()
    assert isinstance(repository, ApiTriggerRepository)
    assert_that(repository.base_url, equal_to("http://api.test"))


def test_create_api_without_url_fails():
    factory = _factory()
    with raises(ValueError) as error:
        factory.create("api")
    assert_that(str(error.value), contains_string("MRMKT_API_URL"))


def test_create_unknown_name_lists_available():
    factory = _factory()
    with raises(ValueError) as error:
        factory.create("carrier-pigeon")
    assert_that(str(error.value), contains_string("postgres"))
    assert_that(str(error.value), contains_string("api"))


def test_create_normalizes_name():
    factory = _factory(api_url="http://api.test")
    assert_that(factory.create("  API  "), instance_of(ApiTriggerProvider))
    assert_that(factory.create("Postgres"), instance_of(PostgresTriggerProvider))


def test_available_lists_backends():
    assert_that(_factory().available(), equal_to(["api", "postgres"]))


def test_register_adds_backend():
    factory = _factory()
    sentinel = PostgresTriggerProvider(InMemoryFinancialRepository())
    factory.register("custom", lambda: sentinel)
    assert_that(factory.create("custom"), is_(sentinel))
    assert_that(factory.available(), equal_to(["api", "custom", "postgres"]))


def test_postgres_close_delegates_to_release():
    calls = []
    provider = PostgresTriggerProvider(
        InMemoryFinancialRepository(), release=lambda: calls.append("closed")
    )
    provider.close()
    assert_that(calls, equal_to(["closed"]))


def test_api_close_is_noop():
    provider = ApiTriggerProvider(ApiTriggerRepository("http://api.test"))
    provider.close()
