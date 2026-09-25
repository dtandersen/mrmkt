import pytest

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from tests.fakes import FakeAlpacaClient


@pytest.fixture
def financial_repository() -> InMemoryFinancialRepository:
    """Provide a fresh in-memory financial repository for a test."""
    return InMemoryFinancialRepository()


@pytest.fixture
def alpaca_client() -> FakeAlpacaClient:
    """Provide a fresh fake Alpaca trading client for a test."""
    return FakeAlpacaClient()
