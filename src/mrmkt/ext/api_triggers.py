"""Trigger repository over the JSON API (for CLI use away from Postgres).

The cluster runs the watcher against Postgres while operators point
their local CLI at the web service: commands execute locally against
this repository, which translates each repository call into an HTTP
request carrying DTOs (never entities). Server-side ``400`` errors map
to ``ValueError`` so commands report them as invalid data, exactly like
local duplicates; transport failures surface as errors.
"""

import requests

from mrmkt.api.trigger_dtos import trigger_from_dto, trigger_to_json
from mrmkt.entity.trigger import Trigger
from mrmkt.repo.triggers import TriggerRepository


class ApiTriggerRepository(TriggerRepository):
    """Implement TriggerRepository over ``/api/triggers`` via requests."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code < 400:
            return
        try:
            errors = response.json().get("errors", [])
        except ValueError:
            errors = []
        detail = "; ".join(errors) if errors else response.text
        message = (
            f"API request failed ({response.status_code}): {detail or 'no detail'}"
        )
        if response.status_code < 500:
            raise ValueError(message)
        raise RuntimeError(message)

    def list_triggers(self, enabled_only: bool = False) -> list[Trigger]:
        params = {"enabled_only": "true" if enabled_only else "false"}
        response = requests.get(
            f"{self.base_url}/api/triggers",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return [trigger_from_dto(item) for item in response.json()]

    def add_trigger(self, trigger: Trigger) -> Trigger:
        response = requests.post(
            f"{self.base_url}/api/triggers",
            json=trigger_to_json(trigger),
            headers=self._headers(),
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return trigger_from_dto(response.json())

    def remove_trigger(self, trigger_id: int) -> bool:
        response = requests.delete(
            f"{self.base_url}/api/triggers/{trigger_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return False
        self._raise_for_status(response)
        return True

    def set_trigger_enabled(self, trigger_id: int, enabled: bool) -> bool:
        response = requests.patch(
            f"{self.base_url}/api/triggers/{trigger_id}",
            json={"enabled": enabled},
            headers=self._headers(),
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return False
        self._raise_for_status(response)
        return True
