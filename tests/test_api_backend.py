"""Gateway tests for the HTTP backend over the generated client.

Transport is faked with httpx MockTransport (requests_mock cannot see
httpx traffic). A CLI-over-API scenario proves ``trigger`` commands run
unchanged against the HTTP backend, and a live-server section covers
the bearer-token guard without monkeypatch.
"""

import secrets
import threading
from shlex import split

import httpx
import pytest
import requests
import uvicorn
from hamcrest import assert_that, contains_string, equal_to
from tests.test_web_api_bdd import _free_port, _wait_for_server
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.trigger import Trigger
from mrmkt.ext.api_gen.client import AuthenticatedClient, Client
from mrmkt.ext.backend.api import ApiMrMktBackend
from mrmkt.web.app import create_web_app

TEST_API_TOKEN = secrets.token_hex(16)


def _stored_dto(**overrides):
    dto = {
        "id": 7,
        "name": "dip-watch",
        "symbol": "AAA",
        "indicator": "risk-range",
        "operator": "crossing-down",
        "value": None,
        "frequency": "once_per_rearm",
        "expires_at": None,
        "message": "",
        "enabled": True,
    }
    dto.update(overrides)
    return dto


def _backend(respond, token=None):
    # NOTE: headers ride on the injected client: set_httpx_client bypasses
    # the generated client's own token->header wiring (mirrored here).
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    inner = httpx.Client(
        transport=httpx.MockTransport(respond),
        base_url="http://api.test",
        headers=headers,
    )
    if token is not None:
        client = AuthenticatedClient(base_url="http://api.test", token=token)
    else:
        client = Client(base_url="http://api.test")
    client.set_httpx_client(inner)
    return ApiMrMktBackend(client)


def test_list_round_trip():
    def respond(request):
        assert_that(request.url.params["enabled_only"], equal_to("false"))
        return httpx.Response(
            200, json=[_stored_dto(), _stored_dto(id=8, name="other", enabled=False)]
        )

    triggers = _backend(respond).list_triggers()
    assert_that([t.name for t in triggers], equal_to(["dip-watch", "other"]))
    assert_that(triggers[0].id, equal_to(7))
    assert_that(triggers[0].enabled, equal_to(True))


def test_enabled_only_passes_query():
    def respond(request):
        assert_that(request.url.params["enabled_only"], equal_to("true"))
        return httpx.Response(200, json=[_stored_dto()])

    triggers = _backend(respond).list_triggers(enabled_only=True)
    assert_that(len(triggers), equal_to(1))


def test_add_round_trip():
    seen = {}

    def respond(request):
        seen["body"] = request.read().decode()
        return httpx.Response(201, json=_stored_dto())

    stored = _backend(respond).add_trigger(
        Trigger(
            id=None,
            name="dip-watch",
            symbol="AAA",
            indicator="risk-range",
            operator="crossing-down",
            value=None,
            frequency="once_per_rearm",
            expires_at=None,
            message="",
            enabled=True,
        )
    )
    assert_that(stored.id, equal_to(7))
    assert_that(seen["body"], contains_string('"symbol":"AAA"'))


def test_add_invalid_data_raises_value_error():
    def respond(request):
        return httpx.Response(
            400, json={"errors": ["operator: 'sideways' is an invalid operator"]}
        )

    try:
        _backend(respond).add_trigger(
            Trigger(
                id=None,
                name="dip-watch",
                symbol="AAA",
                indicator="risk-range",
                operator="sideways",
                value=None,
                frequency="once_per_rearm",
                expires_at=None,
                message="",
                enabled=True,
            )
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert_that(str(error), contains_string("invalid operator"))


def test_server_error_raises_runtime_error():
    def respond(request):
        return httpx.Response(500, json={"errors": ["boom"]})

    try:
        _backend(respond).list_triggers()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert_that(str(error), contains_string("500"))


def test_transport_failure_propagates():
    def respond(request):
        raise httpx.ConnectError("down")

    try:
        _backend(respond).list_triggers()
        raise AssertionError("expected httpx.ConnectError")
    except httpx.ConnectError:
        pass


def test_remove_true_and_missing_false():
    def respond(request):
        if request.url.path.endswith("/999"):
            return httpx.Response(404, json={"errors": ["no trigger with id 999"]})
        return httpx.Response(200, json=_stored_dto())

    backend = _backend(respond)
    assert_that(backend.remove_trigger(7), equal_to(True))
    assert_that(backend.remove_trigger(999), equal_to(False))


def test_toggle_true_and_missing_false():
    def respond(request):
        if request.url.path.endswith("/999"):
            return httpx.Response(404, json={"errors": ["no trigger with id 999"]})
        return httpx.Response(200, json=_stored_dto())

    backend = _backend(respond)
    assert_that(backend.set_trigger_enabled(7, False), equal_to(True))
    assert_that(backend.set_trigger_enabled(999, False), equal_to(False))


def test_bearer_token_sent_when_configured():
    seen = {}

    def respond(request):
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json=[])

    _backend(respond, token=TEST_API_TOKEN).list_triggers()
    assert_that(seen["authorization"], equal_to(f"Bearer {TEST_API_TOKEN}"))


def test_no_auth_header_without_token():
    seen = {}

    def respond(request):
        seen["present"] = "authorization" in request.headers
        return httpx.Response(200, json=[])

    _backend(respond).list_triggers()
    assert_that(seen["present"], equal_to(False))


def test_cli_create_runs_against_the_api(financial_repository):
    def respond(request):
        return httpx.Response(201, json=_stored_dto())

    deps = cli_dependencies_for_testing(
        repository=financial_repository,
        triggers=_backend(respond),
    )
    result = CliRunner().invoke(
        cli.app,
        split(
            "mrmkt trigger create dip-watch "
            "--symbol AAA --indicator risk-range --operator crossing-down"
        )[1:],
        obj=deps,
        env={"COLUMNS": "80"},
    )
    assert_that(result.exit_code, equal_to(0))
    assert_that(
        result.output,
        contains_string("dip-watch,AAA,risk-range,crossing-down,,once_per_rearm"),
    )


def test_cli_list_runs_against_the_api(financial_repository):
    def respond(request):
        return httpx.Response(200, json=[_stored_dto()])

    deps = cli_dependencies_for_testing(
        repository=financial_repository,
        triggers=_backend(respond),
    )
    result = CliRunner().invoke(
        cli.app, split("mrmkt trigger list")[1:], obj=deps, env={"COLUMNS": "80"}
    )
    assert_that(result.exit_code, equal_to(0))
    assert_that(result.output, contains_string("dip-watch,AAA,risk-range"))


@pytest.fixture
def secured_api(financial_repository):
    deps = cli_dependencies_for_testing(repository=financial_repository)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_web_app(lambda: deps, api_token=TEST_API_TOKEN),
            host="127.0.0.1",
            port=port,
            log_level="error",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_server("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def test_api_without_token_is_rejected(secured_api):
    response = requests.get(f"{secured_api}/api/triggers", timeout=10)
    assert_that(response.status_code, equal_to(401))


def test_api_with_wrong_token_is_rejected(secured_api):
    response = requests.get(
        f"{secured_api}/api/triggers",
        headers={"Authorization": "Bearer wrong"},
        timeout=10,
    )
    assert_that(response.status_code, equal_to(401))


def test_api_with_token_succeeds(secured_api):
    response = requests.get(
        f"{secured_api}/api/triggers",
        headers={"Authorization": f"Bearer {TEST_API_TOKEN}"},
        timeout=10,
    )
    assert_that(response.status_code, equal_to(200))
    assert_that(response.json(), equal_to([]))
