"""Shared fixtures for trigger CLI BDD.

Step implementations live in ``tests/cli/cli_steps/trigger_cli_steps.py``;
each feature runner imports the step functions it uses and registers them
itself. No monkeypatching: tests inject fakes through the ``CliRunner``
``obj``/``env`` seam.

The fixture hands out the in-memory repository through a repository factory
that counts every release, so scenarios can assert the CLI released it.
"""

from types import SimpleNamespace

import pytest

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository


@pytest.fixture
def trigger_context():
    context = SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
        generated_trigger_name=None,
        generated_trigger_set_name=None,
        repository_closes=0,
        repository_factory=None,
    )

    def repository_factory():
        """Return the shared in-memory repository and a counting release callable."""

        def close_repository() -> None:
            context.repository_closes += 1

        return context.local, close_repository

    context.repository_factory = repository_factory
    return context
