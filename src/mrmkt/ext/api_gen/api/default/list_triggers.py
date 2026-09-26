from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_dto import ErrorDto
from ...models.trigger_dto import TriggerDto
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    enabled_only: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["enabled_only"] = enabled_only

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/triggers",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | list[TriggerDto] | ErrorDto | None:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> Any | list[TriggerDto]:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                response_200_type_0 = []
                _response_200_type_0 = data
                for response_200_type_0_item_data in _response_200_type_0:
                    response_200_type_0_item = TriggerDto.from_dict(
                        response_200_type_0_item_data
                    )

                    response_200_type_0.append(response_200_type_0_item)

                return response_200_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(Any | list[TriggerDto], data)

        response_200 = _parse_response_200(response.json())

        return response_200

    if response.status_code == 500:
        response_500 = ErrorDto.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | list[TriggerDto] | ErrorDto]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    enabled_only: bool | Unset = False,
) -> Response[Any | list[TriggerDto] | ErrorDto]:
    """ListTriggers

    Args:
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[TriggerDto] | ErrorDto]
    """

    kwargs = _get_kwargs(
        enabled_only=enabled_only,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    enabled_only: bool | Unset = False,
) -> Any | list[TriggerDto] | ErrorDto | None:
    """ListTriggers

    Args:
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[TriggerDto] | ErrorDto
    """

    return sync_detailed(
        client=client,
        enabled_only=enabled_only,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    enabled_only: bool | Unset = False,
) -> Response[Any | list[TriggerDto] | ErrorDto]:
    """ListTriggers

    Args:
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[TriggerDto] | ErrorDto]
    """

    kwargs = _get_kwargs(
        enabled_only=enabled_only,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    enabled_only: bool | Unset = False,
) -> Any | list[TriggerDto] | ErrorDto | None:
    """ListTriggers

    Args:
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[TriggerDto] | ErrorDto
    """

    return (
        await asyncio_detailed(
            client=client,
            enabled_only=enabled_only,
        )
    ).parsed
