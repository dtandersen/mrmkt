"""BDD coverage for the trigger JSON API (uvicorn + requests, no browser)."""

import http.client
import logging
import socket
import threading
import time
from types import SimpleNamespace

import pytest
import requests
import uvicorn
from hamcrest import assert_that, contains_string, equal_to, has_item, has_length
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.web.app import create_web_app

scenarios("features/web/api_triggers.feature")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(host, port, timeout=10.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            connection = http.client.HTTPConnection(host, port, timeout=1)
            try:
                connection.request("GET", "/")
                status = connection.getresponse().status
            finally:
                connection.close()
            if status < 500:
                return
        except Exception as error:
            logging.debug("waiting for web server: %s", error)
        if time.monotonic() > deadline:
            raise TimeoutError(f"web server did not start on {host}:{port}")
        time.sleep(0.05)


@pytest.fixture
def api_context(financial_repository):
    deps = cli_dependencies_for_testing(repository=financial_repository)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_web_app(lambda: deps),
            host="127.0.0.1",
            port=port,
            log_level="error",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_server("127.0.0.1", port)
    context = SimpleNamespace(
        base_url=f"http://127.0.0.1:{port}",
        response=None,
        created_id=None,
    )
    yield context
    server.should_exit = True
    thread.join(timeout=10)


def _table_options(datatable):
    return {str(row[0]): str(row[1]) for row in datatable[1:]}


@given("the JSON API is running")
def api_is_running(api_context):
    assert_that(api_context.base_url, contains_string("http://127.0.0.1:"))


def _create_payload(options):
    payload = {
        "symbol": options["symbol"],
        "indicator": options.get("indicator", "risk-range"),
        "operator": options.get("operator", "crossing-down"),
        "frequency": options.get("frequency", "once_per_rearm"),
        "message": options.get("message", ""),
    }
    if options.get("name"):
        payload["name"] = options["name"]
    if options.get("value"):
        payload["value"] = float(options["value"])
    if options.get("expires"):
        payload["expires"] = options["expires"]
    return payload


@when("I create a trigger via the API with:")
def api_create_trigger(api_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "value"]))
    api_context.response = requests.post(
        f"{api_context.base_url}/api/triggers",
        json=_create_payload(_table_options(datatable)),
        timeout=10,
    )
    try:
        body = api_context.response.json()
    except ValueError:
        body = None
    if isinstance(body, dict) and body.get("id") is not None:
        api_context.created_id = body["id"]


@when("I list triggers via the API")
def api_list_triggers(api_context):
    api_context.response = requests.get(
        f"{api_context.base_url}/api/triggers", timeout=10
    )


@when("I list enabled triggers via the API")
def api_list_enabled_triggers(api_context):
    api_context.response = requests.get(
        f"{api_context.base_url}/api/triggers",
        params={"enabled_only": "true"},
        timeout=10,
    )


@when(parsers.parse("I delete trigger id {trigger_id:d} via the API"))
def api_delete_trigger(api_context, trigger_id):
    api_context.response = requests.delete(
        f"{api_context.base_url}/api/triggers/{trigger_id}", timeout=10
    )


@when("I delete the created trigger via the API")
def api_delete_created_trigger(api_context):
    assert_that(api_context.created_id is not None, equal_to(True))
    api_context.response = requests.delete(
        f"{api_context.base_url}/api/triggers/{api_context.created_id}", timeout=10
    )


@when("I disable the created trigger via the API")
def api_disable_created_trigger(api_context):
    assert_that(api_context.created_id is not None, equal_to(True))
    api_context.response = requests.patch(
        f"{api_context.base_url}/api/triggers/{api_context.created_id}",
        json={"enabled": False},
        timeout=10,
    )


@when(parsers.parse("I set trigger id {trigger_id:d} enabled via the API"))
def api_enable_trigger(api_context, trigger_id):
    api_context.response = requests.patch(
        f"{api_context.base_url}/api/triggers/{trigger_id}",
        json={"enabled": True},
        timeout=10,
    )


@then(parsers.parse("the API response status is {status:d}"))
def api_response_status(api_context, status):
    assert_that(api_context.response.status_code, equal_to(status))


@then("the API response contains:")
def api_response_contains(api_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "value"]))
    body = api_context.response.json()
    for row in datatable[1:]:
        field, value = str(row[0]), str(row[1])
        actual = body[field]
        if isinstance(actual, bool):
            assert_that(actual, equal_to(value == "true"))
        elif actual is None:
            assert_that(value, equal_to(""))
        else:
            assert_that(str(actual), equal_to(value))


@then(parsers.parse('the API response errors mention "{text}"'))
def api_response_errors_mention(api_context, text):
    body = api_context.response.json()
    assert_that("; ".join(body.get("errors", [])), contains_string(text))


@then("the API list is empty")
def api_list_is_empty(api_context):
    assert_that(api_context.response.json(), has_length(0))


@then(parsers.parse('the API list contains trigger "{name}"'))
def api_list_contains_trigger(api_context, name):
    names = [item["name"] for item in api_context.response.json()]
    assert_that(names, has_item(name))
