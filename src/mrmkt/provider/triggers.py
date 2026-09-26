"""Trigger repository backend selection.

The composition root manages triggers against Postgres locally or over
HTTP remotely (cluster-hosted watcher). Both backends hide behind
:class:`TriggerRepositoryProvider` so command construction never learns
which store is in use; only this module and composition know.

Lifecycle: the shared local repository is app-scoped and released by
the composition root, so providers default to a no-op close. Pass an
explicit ``release`` only when the provider owns a dedicated backend.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from mrmkt.repo.triggers import TriggerRepository


class TriggerRepositoryProvider(ABC):
    """Vend a trigger repository backend plus its release."""

    @abstractmethod
    def triggers(self) -> TriggerRepository:
        """Return the backend repository."""

    @abstractmethod
    def close(self) -> None:
        """Release backend resources, if any."""


class PostgresTriggerProvider(TriggerRepositoryProvider):
    """Vend a Postgres-backed repository (usually the shared local one)."""

    def __init__(
        self,
        repository: TriggerRepository,
        release: Callable[[], None] = lambda: None,
    ):
        self._repository = repository
        self._release = release

    def triggers(self) -> TriggerRepository:
        return self._repository

    def close(self) -> None:
        self._release()


class ApiTriggerProvider(TriggerRepositoryProvider):
    """Vend an HTTP-backed repository (stateless; nothing to release)."""

    def __init__(self, repository: TriggerRepository):
        self._repository = repository

    def triggers(self) -> TriggerRepository:
        return self._repository

    def close(self) -> None:
        pass


def resolve_trigger_provider(
    api: TriggerRepository | None,
    local_repository: TriggerRepository,
    local_release: Callable[[], None] = lambda: None,
) -> TriggerRepositoryProvider:
    """Select the API backend when provided, else the local Postgres one.

    Takes explicit inputs (no environment reads) so selection stays a
    pure, directly testable decision; composition reads the environment
    and passes the values in.
    """
    if api is not None:
        return ApiTriggerProvider(api)
    return PostgresTriggerProvider(local_repository, local_release)
