"""HTTP Mr Market backend over the generated OpenAPI client.

Status interpretation stays here (the generator models bodies, never
domain mapping): 404 means absent (``False``), other 4xx mean invalid
data (``ValueError``), 5xx mean failure. Symbol methods raise until the
symbol endpoints exist (tracked as next slice).
"""

from mrmkt.api.trigger_dtos import trigger_from_dto
from mrmkt.backend import MrMktBackend
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import Trigger
from mrmkt.ext.api_gen.api.default import (
    create_trigger,
    delete_trigger,
    list_triggers,
    set_trigger_enabled,
)
from mrmkt.ext.api_gen.client import AuthenticatedClient, Client
from mrmkt.ext.api_gen.models.create_trigger_dto import (
    CreateTriggerDto as GeneratedCreate,
)
from mrmkt.ext.api_gen.models.error_dto import ErrorDto as GeneratedError
from mrmkt.ext.api_gen.models.set_enabled_dto import (
    SetEnabledDto as GeneratedSetEnabled,
)
from mrmkt.ext.api_gen.models.trigger_dto import TriggerDto as GeneratedTrigger
from mrmkt.ext.api_gen.types import Response


class ApiMrMktBackend(MrMktBackend):
    """Serve repositories through generated endpoints; close the session."""

    def __init__(self, client: AuthenticatedClient | Client):
        self._client = client

    def _raise_for_status(self, response: Response) -> None:
        status = int(response.status_code)
        if status < 400:
            return
        errors = (
            list(response.parsed.errors)
            if isinstance(response.parsed, GeneratedError)
            else []
        )
        detail = "; ".join(errors) if errors else "no detail"
        message = f"API request failed ({status}): {detail}"
        if status < 500:
            raise ValueError(message)
        raise RuntimeError(message)

    def _trigger(self, response: Response) -> Trigger:
        parsed = response.parsed
        if not isinstance(parsed, GeneratedTrigger):
            raise RuntimeError(
                f"API request failed ({int(response.status_code)}): no detail"
            )
        return trigger_from_dto(parsed.to_dict())

    def list_triggers(self, enabled_only: bool = False) -> list[Trigger]:
        response = list_triggers.sync_detailed(
            client=self._client, enabled_only=enabled_only
        )
        self._raise_for_status(response)
        parsed = response.parsed
        if not isinstance(parsed, list):
            raise RuntimeError(
                f"API request failed ({int(response.status_code)}): no detail"
            )
        return [trigger_from_dto(item.to_dict()) for item in parsed]

    def add_trigger(self, trigger: Trigger) -> Trigger:
        response = create_trigger.sync_detailed(
            client=self._client,
            body=GeneratedCreate(
                name=trigger.name,
                symbol=trigger.symbol,
                indicator=trigger.indicator,
                operator=trigger.operator,
                value=trigger.value,
                frequency=trigger.frequency,
                expires=trigger.expires_at.isoformat() if trigger.expires_at else None,
                message=trigger.message,
            ),
        )
        self._raise_for_status(response)
        return self._trigger(response)

    def remove_trigger(self, trigger_id: int) -> bool:
        response = delete_trigger.sync_detailed(
            client=self._client, trigger_id=trigger_id
        )
        if int(response.status_code) == 404:
            return False
        self._raise_for_status(response)
        return True

    def set_trigger_enabled(self, trigger_id: int, enabled: bool) -> bool:
        response = set_trigger_enabled.sync_detailed(
            client=self._client,
            trigger_id=trigger_id,
            body=GeneratedSetEnabled(enabled=enabled),
        )
        if int(response.status_code) == 404:
            return False
        self._raise_for_status(response)
        return True

    def get_symbols(self) -> list[str]:
        raise NotImplementedError("symbol API not yet available")

    def get_tickers(self) -> list[Ticker]:
        raise NotImplementedError("symbol API not yet available")

    def add_ticker(self, ticker: Ticker):
        raise NotImplementedError("symbol API not yet available")

    def close(self) -> None:
        """Close the generated client's cached sync session, if built."""
        if self._client._client is not None:
            self._client._client.close()
