from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from typing_extensions import Self

T = TypeVar("T", bound="TriggerDto")


@_attrs_define
class TriggerDto:
    """
    Attributes:
        id (int | None):
        name (str):
        symbol (str):
        indicator (str):
        operator (str):
        value (float | None):
        frequency (str):
        expires_at (None | str):
        message (str):
        enabled (bool):
    """

    id: int | None
    name: str
    symbol: str
    indicator: str
    operator: str
    value: float | None
    frequency: str
    expires_at: None | str
    message: str
    enabled: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: int | None
        id = self.id

        name = self.name

        symbol = self.symbol

        indicator = self.indicator

        operator = self.operator

        value: float | None
        value = self.value

        frequency = self.frequency

        expires_at: None | str
        expires_at = self.expires_at

        message = self.message

        enabled = self.enabled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "symbol": symbol,
                "indicator": indicator,
                "operator": operator,
                "value": value,
                "frequency": frequency,
                "expires_at": expires_at,
                "message": message,
                "enabled": enabled,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls, src_dict: Mapping[str, Any]) -> Self:
        d = dict(src_dict)

        def _parse_id(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        id = _parse_id(d.pop("id"))

        name = d.pop("name")

        symbol = d.pop("symbol")

        indicator = d.pop("indicator")

        operator = d.pop("operator")

        def _parse_value(data: object) -> float | None:
            if data is None:
                return data
            return cast(float | None, data)

        value = _parse_value(d.pop("value"))

        frequency = d.pop("frequency")

        def _parse_expires_at(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        expires_at = _parse_expires_at(d.pop("expires_at"))

        message = d.pop("message")

        enabled = d.pop("enabled")

        trigger_dto = cls(
            id=id,
            name=name,
            symbol=symbol,
            indicator=indicator,
            operator=operator,
            value=value,
            frequency=frequency,
            expires_at=expires_at,
            message=message,
            enabled=enabled,
        )

        trigger_dto.additional_properties = d
        return trigger_dto

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
