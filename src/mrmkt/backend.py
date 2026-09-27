"""Mr Market backend interface (whole service, not one resource).

A backend IS-A bundle of repository interfaces: commands keep their
narrow parameters while composition passes a single object everywhere.
Postgres satisfies this with the existing shared repository; the API
backend implements it over HTTP, resource by resource.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from httpx import Timeout

from mrmkt.repo.financials import FinancialRepository
from mrmkt.repo.prices import PriceRepository
from mrmkt.repo.tags import TickerTagRepository
from mrmkt.repo.tickers import TickerRepository
from mrmkt.repo.trigger_sets import TriggerSetRepository
from mrmkt.repo.triggers import TriggerRepository

__all__ = ["MrMktBackend", "MrMktBackendFactory"]


class MrMktBackend(
    TriggerRepository,
    TickerRepository,
    FinancialRepository,
    PriceRepository,
    TickerTagRepository,
    TriggerSetRepository,
    ABC,
):
    """Whole-service backend: every repository interface plus release."""

    @abstractmethod
    def close(self) -> None:
        """Release backend resources, if any."""


class MrMktBackendFactory:
    """Build Mr Market backends by name.

    ``create("postgres")`` returns the shared local backend as-is,
    ``create("api")`` builds the HTTP backend (needs ``api_url``). Extra
    backends register via :meth:`register`. Names normalize to
    lowercase; unknown names raise ``ValueError`` listing available
    backends. Takes explicit inputs (no environment reads) so selection
    stays directly testable; composition reads the environment.
    """

    def __init__(
        self,
        local_repository: MrMktBackend,
        local_release: Callable[[], None] = lambda: None,
        api_url: str | None = None,
        api_token: str | None = None,
    ):
        self._local_repository = local_repository
        self._local_release = local_release
        self._api_url = (api_url or "").strip() or None
        self._api_token = api_token or None
        self._builders: dict[str, Callable[[], MrMktBackend]] = {
            "postgres": lambda: local_repository,
            "api": self._build_api_backend,
        }

    def register(self, name: str, builder: Callable[[], MrMktBackend]) -> None:
        """Register an additional backend under ``name``."""
        self._builders[name.strip().lower()] = builder

    def available(self) -> list[str]:
        """Backend names this factory can build, sorted."""
        return sorted(self._builders)

    def create(self, name: str) -> MrMktBackend:
        """Build the named backend; ValueError lists available names."""
        normalized = (name or "").strip().lower()
        try:
            builder = self._builders[normalized]
        except KeyError:
            raise ValueError(
                f"unknown mrmkt backend {name!r} "
                f"(available: {', '.join(self.available())})"
            ) from None
        return builder()

    def _build_api_backend(self) -> MrMktBackend:
        # Local import: the interface module must not depend on ext at load.
        from mrmkt.ext.api_gen.client import AuthenticatedClient, Client
        from mrmkt.ext.backend.api import ApiMrMktBackend

        if self._api_url is None:
            raise ValueError(
                "mrmkt backend 'api' needs MRMKT_API_URL "
                f"(available: {', '.join(self.available())})"
            )
        if self._api_token is not None:
            client: AuthenticatedClient | Client = AuthenticatedClient(
                base_url=self._api_url,
                token=self._api_token,
                timeout=Timeout(10.0),
            )
        else:
            client = Client(base_url=self._api_url, timeout=Timeout(10.0))
        return ApiMrMktBackend(client)
