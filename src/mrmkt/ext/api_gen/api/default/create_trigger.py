from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_trigger_dto import CreateTriggerDto
from ...models.error_dto import ErrorDto
from ...models.trigger_dto import TriggerDto
from ...types import Response


def _get_kwargs(
    *,
    body: CreateTriggerDto,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/triggers",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | TriggerDto | ErrorDto | None:
    if response.status_code == 201:

        def _parse_response_201(data: object) -> Any | TriggerDto:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_201_type_0 = TriggerDto.from_dict(data)

                return response_201_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(Any | TriggerDto, data)

        response_201 = _parse_response_201(response.json())

        return response_201

    if response.status_code == 400:
        response_400 = ErrorDto.from_dict(response.json())

        return response_400

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | TriggerDto | ErrorDto]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateTriggerDto,
) -> Response[Any | TriggerDto | ErrorDto]:
    """CreateTrigger

    Args:
        body (CreateTriggerDto):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | TriggerDto | ErrorDto]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: CreateTriggerDto,
) -> Any | TriggerDto | ErrorDto | None:
    """CreateTrigger

    Args:
        body (CreateTriggerDto):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | TriggerDto | ErrorDto
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateTriggerDto,
) -> Response[Any | TriggerDto | ErrorDto]:
    """CreateTrigger

    Args:
        body (CreateTriggerDto):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | TriggerDto | ErrorDto]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CreateTriggerDto,
) -> Any | TriggerDto | ErrorDto | None:
    """CreateTrigger

    Args:
        body (CreateTriggerDto):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | TriggerDto | ErrorDto
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
