"""Shared fixtures for trigger CLI BDD.

Step implementations live in ``tests/cli/cli_steps/trigger_cli_steps.py``;
each feature runner imports the step functions it uses and registers them
itself. No monkeypatching: tests inject fakes through the ``CliRunner``
``obj``/``env`` seam.
"""

from types import SimpleNamespace

import pytest

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository


@pytest.fixture
def trigger_context():
    return SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
        generated_trigger_name=None,
        generated_trigger_set_name=None,
    )
