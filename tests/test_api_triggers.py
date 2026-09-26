"""Gateway tests for the HTTP trigger repository (requests_mock).

The repository is an API gateway to a service the suite does not own,
so requests_mock stands in for the wire. A CLI-over-API scenario proves
``trigger`` commands run unchanged against the HTTP repository, and a
live-server section covers the bearer-token guard without monkeypatch.
"""

import secrets
import threading
from shlex import split

import pytest
import requests
import uvicorn
from hamcrest import assert_that, contains_string, equal_to
from tests.test_web_api_bdd import _free_port, _wait_for_server
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.trigger import Trigger
from mrmkt.ext.api_triggers import ApiTriggerRepository
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


def test_list_round_trip(requests_mock):
    requests_mock.get(
        "http://api.test/api/triggers?enabled_only=false",
        json=[_stored_dto(), _stored_dto(id=8, name="other", enabled=False)],
    )
    triggers = ApiTriggerRepository("http://api.test").list_triggers()
    assert_that([t.name for t in triggers], equal_to(["dip-watch", "other"]))
    assert_that(triggers[0].id, equal_to(7))
    assert_that(triggers[0].enabled, equal_to(True))


def test_enabled_only_passes_query(requests_mock):
    requests_mock.get(
        "http://api.test/api/triggers?enabled_only=true",
        json=[_stored_dto()],
    )
    triggers = ApiTriggerRepository("http://api.test").list_triggers(enabled_only=True)
    assert_that(len(triggers), equal_to(1))


def test_add_round_trip(requests_mock):
    posted = requests_mock.post(
        "http://api.test/api/triggers", json=_stored_dto(), status_code=201
    )
    stored = ApiTriggerRepository("http://api.test").add_trigger(
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
    assert_that(posted.last_request.json()["symbol"], equal_to("AAA"))


def test_add_invalid_data_raises_value_error(requests_mock):
    requests_mock.post(
        "http://api.test/api/triggers",
        json={"errors": ["operator: 'sideways' is an invalid operator"]},
        status_code=400,
    )
    try:
        ApiTriggerRepository("http://api.test").add_trigger(
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


def test_server_error_raises_runtime_error(requests_mock):
    requests_mock.get(
        "http://api.test/api/triggers?enabled_only=false",
        text="boom",
        status_code=500,
    )
    try:
        ApiTriggerRepository("http://api.test").list_triggers()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert_that(str(error), contains_string("500"))


def test_remove_true_and_missing_false(requests_mock):
    requests_mock.delete("http://api.test/api/triggers/7", json={})
    requests_mock.delete("http://api.test/api/triggers/999", status_code=404)
    repository = ApiTriggerRepository("http://api.test")
    assert_that(repository.remove_trigger(7), equal_to(True))
    assert_that(repository.remove_trigger(999), equal_to(False))


def test_toggle_true_and_missing_false(requests_mock):
    requests_mock.patch("http://api.test/api/triggers/7", json=_stored_dto())
    requests_mock.patch("http://api.test/api/triggers/999", status_code=404)
    repository = ApiTriggerRepository("http://api.test")
    assert_that(repository.set_trigger_enabled(7, False), equal_to(True))
    assert_that(repository.set_trigger_enabled(999, False), equal_to(False))


def test_bearer_token_sent_when_configured(requests_mock):
    adapter = requests_mock.get(
        "http://api.test/api/triggers?enabled_only=false", json=[]
    )
    ApiTriggerRepository("http://api.test", token=TEST_API_TOKEN).list_triggers()
    assert_that(
        adapter.last_request.headers.get("Authorization"),
        equal_to(f"Bearer {TEST_API_TOKEN}"),
    )


def test_no_auth_header_without_token(requests_mock):
    adapter = requests_mock.get(
        "http://api.test/api/triggers?enabled_only=false", json=[]
    )
    ApiTriggerRepository("http://api.test").list_triggers()
    assert_that("Authorization" in adapter.last_request.headers, equal_to(False))


def test_cli_create_runs_against_the_api(requests_mock, financial_repository):
    requests_mock.post(
        "http://api.test/api/triggers", json=_stored_dto(), status_code=201
    )
    deps = cli_dependencies_for_testing(
        repository=financial_repository,
        triggers=ApiTriggerRepository("http://api.test"),
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


def test_cli_list_runs_against_the_api(requests_mock, financial_repository):
    requests_mock.get(
        "http://api.test/api/triggers?enabled_only=false", json=[_stored_dto()]
    )
    deps = cli_dependencies_for_testing(
        repository=financial_repository,
        triggers=ApiTriggerRepository("http://api.test"),
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
