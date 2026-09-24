"""Composition root for trigger CLI dependencies (outer layer).

CLI handlers never construct repositories or name generators directly:
they resolve a :class:`TriggerCliDependencies` through
:func:`resolve_trigger_dependencies`, which returns the injected object
from the Typer context (``CliRunner(..., obj=...)`` in tests) or the
production defaults. Tests supply an in-memory repository factory,
deterministic name generators, and a pinned terminal width via the
``CliRunner`` call — no monkeypatching.
"""

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import typer

from mrmkt.command import _shared
from mrmkt.command.create_trigger import CreateTrigger
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.command.triggersets_common import _default_set_name


@dataclass(frozen=True)
class TriggerCliDependencies:
    """Injectable trigger-path dependencies (repository + name generators)."""

    repository_factory: Callable[[], tuple[Any, Callable[[], None]]]
    trigger_name_generator: Callable[[], str]
    triggerset_name_generator: Callable[[], str]


def default_trigger_dependencies() -> TriggerCliDependencies:
    """Production wiring: concrete repository factory and random generators."""
    return TriggerCliDependencies(
        repository_factory=_shared.create_local_ticker_repository,
        trigger_name_generator=_default_trigger_name,
        triggerset_name_generator=_default_set_name,
    )


def resolve_trigger_dependencies(ctx: typer.Context | None) -> TriggerCliDependencies:
    """Return injected dependencies from the Typer context, else defaults."""
    obj = getattr(ctx, "obj", None)
    if isinstance(obj, TriggerCliDependencies):
        return obj
    return default_trigger_dependencies()


@contextmanager
def create_trigger_command(
    deps: TriggerCliDependencies | None = None,
):
    """Yield a ready ``CreateTrigger``; close the repository afterwards."""
    resolved = deps if deps is not None else default_trigger_dependencies()
    repository, close_repository = resolved.repository_factory()
    try:
        yield CreateTrigger(repository, name_generator=resolved.trigger_name_generator)
    finally:
        close_repository()
