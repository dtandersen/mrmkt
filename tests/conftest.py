import pytest

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository


@pytest.fixture
def financial_repository() -> InMemoryFinancialRepository:
    """Provide a fresh in-memory financial repository for a test."""
    return InMemoryFinancialRepository()
