import pytest
from tests.fakes import FakeAlpacaClient, FakeMessageQueue

from mrmkt.ext.backend import InMemoryBackend


@pytest.fixture
def financial_repository() -> InMemoryBackend:
    """Provide a fresh in-memory financial repository for a test."""
    return InMemoryBackend()


@pytest.fixture
def alpaca_client() -> FakeAlpacaClient:
    """Provide a fresh fake Alpaca trading client for a test."""
    return FakeAlpacaClient()


@pytest.fixture
def fake_queue() -> FakeMessageQueue:
    """Provide a fresh fake message queue for a test."""
    return FakeMessageQueue()
