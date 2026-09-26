"""Unit tests for the Mr Market backend factory (string in, backend out).

The factory takes explicit inputs (no environment reads), so selection
is covered directly with the in-memory fake repository. No mocks, no
environment mutation.
"""

from hamcrest import assert_that, contains_string, equal_to, instance_of, is_
from pytest import raises

from mrmkt.backend import MrMktBackend
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.ext.backend import ApiMrMktBackend, MrMktBackendFactory


def _factory(local=None, api_url=None, api_token=None):
    return MrMktBackendFactory(
        local_repository=local if local is not None else InMemoryFinancialRepository(),
        api_url=api_url,
        api_token=api_token,
    )


def test_create_postgres_returns_shared_backend():
    local = InMemoryFinancialRepository()
    backend = MrMktBackendFactory(local_repository=local).create("postgres")
    assert_that(backend, instance_of(MrMktBackend))
    assert_that(backend, is_(local))


def test_create_api_builds_http_backend():
    backend = _factory(api_url="http://api.test").create("api")
    assert_that(backend, instance_of(ApiMrMktBackend))
    assert_that(backend, instance_of(MrMktBackend))


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
    assert_that(factory.create("  API  "), instance_of(ApiMrMktBackend))
    assert_that(factory.create("Postgres"), instance_of(MrMktBackend))


def test_available_lists_backends():
    assert_that(_factory().available(), equal_to(["api", "postgres"]))


def test_register_adds_backend():
    factory = _factory()
    sentinel = _factory().create("postgres")
    factory.register("custom", lambda: sentinel)
    assert_that(factory.create("custom"), is_(sentinel))
    assert_that(factory.available(), equal_to(["api", "custom", "postgres"]))


def test_postgres_close_is_shared_noop():
    backend = _factory().create("postgres")
    backend.close()


def test_api_close_closes_session():
    backend = _factory(api_url="http://api.test").create("api")
    backend.close()
