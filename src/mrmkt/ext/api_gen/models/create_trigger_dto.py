from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from typing_extensions import Self

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateTriggerDto")


@_attrs_define
class CreateTriggerDto:
    """
    Attributes:
        name (None | str | Unset):
        symbol (str | Unset):  Default: ''.
        indicator (str | Unset):  Default: ''.
        operator (str | Unset):  Default: 'crossing-down'.
        value (float | None | Unset):
        frequency (str | Unset):  Default: 'once_per_rearm'.
        expires (None | str | Unset):
        message (str | Unset):  Default: ''.
    """

    name: None | str | Unset = UNSET
    symbol: str | Unset = ""
    indicator: str | Unset = ""
    operator: str | Unset = "crossing-down"
    value: float | None | Unset = UNSET
    frequency: str | Unset = "once_per_rearm"
    expires: None | str | Unset = UNSET
    message: str | Unset = ""
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        symbol = self.symbol

        indicator = self.indicator

        operator = self.operator

        value: float | None | Unset
        if isinstance(self.value, Unset):
            value = UNSET
        else:
            value = self.value

        frequency = self.frequency

        expires: None | str | Unset
        if isinstance(self.expires, Unset):
            expires = UNSET
        else:
            expires = self.expires

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if symbol is not UNSET:
            field_dict["symbol"] = symbol
        if indicator is not UNSET:
            field_dict["indicator"] = indicator
        if operator is not UNSET:
            field_dict["operator"] = operator
        if value is not UNSET:
            field_dict["value"] = value
        if frequency is not UNSET:
            field_dict["frequency"] = frequency
        if expires is not UNSET:
            field_dict["expires"] = expires
        if message is not UNSET:
            field_dict["message"] = message

        return field_dict

    @classmethod
    def from_dict(cls, src_dict: Mapping[str, Any]) -> Self:
        d = dict(src_dict)

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        symbol = d.pop("symbol", UNSET)

        indicator = d.pop("indicator", UNSET)

        operator = d.pop("operator", UNSET)

        def _parse_value(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        value = _parse_value(d.pop("value", UNSET))

        frequency = d.pop("frequency", UNSET)

        def _parse_expires(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        expires = _parse_expires(d.pop("expires", UNSET))

        message = d.pop("message", UNSET)

        create_trigger_dto = cls(
            name=name,
            symbol=symbol,
            indicator=indicator,
            operator=operator,
            value=value,
            frequency=frequency,
            expires=expires,
            message=message,
        )

        create_trigger_dto.additional_properties = d
        return create_trigger_dto

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
