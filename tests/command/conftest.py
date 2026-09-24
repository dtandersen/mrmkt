"""Shared fixtures for trigger command BDD.

Step implementations live in ``tests/command/steps/trigger_steps.py``;
each feature runner imports the step functions it uses and registers them
itself. All scenarios run against the in-memory fake repository; no
monkeypatching.
"""

from types import SimpleNamespace

import pytest

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository


@pytest.fixture
def trigger_command_context():
    return SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
        failed=False,
        error="",
        name_generator=None,
    )
