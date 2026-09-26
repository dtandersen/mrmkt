import pytest
from tests.fakes import FakeAlpacaClient, FakeTickSource

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository


@pytest.fixture
def financial_repository() -> InMemoryFinancialRepository:
    """Provide a fresh in-memory financial repository for a test."""
    return InMemoryFinancialRepository()


@pytest.fixture
def alpaca_client() -> FakeAlpacaClient:
    """Provide a fresh fake Alpaca trading client for a test."""
    return FakeAlpacaClient()


@pytest.fixture
def tick_source() -> FakeTickSource:
    """Provide a fresh scripted live-tick source for a test."""
    return FakeTickSource()
