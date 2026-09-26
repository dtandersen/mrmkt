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

from mrmkt.ext.api_triggers import ApiTriggerRepository
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


class TriggerProviderFactory:
    """Build trigger providers by name.

    ``create("postgres")`` vends the local database backend,
    ``create("api")`` the HTTP backend (needs ``api_url``). Extra
    backends register via :meth:`register`. Names normalize to
    lowercase; unknown names raise ``ValueError`` listing available
    backends. Takes explicit inputs (no environment reads) so selection
    stays directly testable; composition reads the environment.
    """

    def __init__(
        self,
        local_repository: TriggerRepository,
        local_release: Callable[[], None] = lambda: None,
        api_url: str | None = None,
        api_token: str | None = None,
    ):
        self._local_repository = local_repository
        self._local_release = local_release
        self._api_url = (api_url or "").strip() or None
        self._api_token = api_token or None
        self._builders: dict[str, Callable[[], TriggerRepositoryProvider]] = {
            "postgres": lambda: PostgresTriggerProvider(
                local_repository, local_release
            ),
            "api": self._build_api_provider,
        }

    def register(
        self, name: str, builder: Callable[[], TriggerRepositoryProvider]
    ) -> None:
        """Register an additional backend under ``name``."""
        self._builders[name.strip().lower()] = builder

    def available(self) -> list[str]:
        """Backend names this factory can build, sorted."""
        return sorted(self._builders)

    def create(self, name: str) -> TriggerRepositoryProvider:
        """Build the named backend; ValueError lists available names."""
        normalized = (name or "").strip().lower()
        try:
            builder = self._builders[normalized]
        except KeyError:
            raise ValueError(
                f"unknown trigger provider {name!r} "
                f"(available: {', '.join(self.available())})"
            ) from None
        return builder()

    def _build_api_provider(self) -> ApiTriggerProvider:
        if self._api_url is None:
            raise ValueError(
                "trigger provider 'api' needs MRMKT_API_URL "
                f"(available: {', '.join(self.available())})"
            )
        return ApiTriggerProvider(
            ApiTriggerRepository(self._api_url, token=self._api_token)
        )
