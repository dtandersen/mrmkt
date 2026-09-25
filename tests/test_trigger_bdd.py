"""BDD coverage for trigger and trigger-set commands and CLI commands."""

from shlex import split
from types import SimpleNamespace
from typing import cast

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    greater_than,
    has_item,
    has_length,
    instance_of,
    is_,
    not_none,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.add_triggerset import AddTriggerToSet
from mrmkt.command.create_trigger import CreateTrigger
from mrmkt.command.create_triggerset import CreateTriggerSet
from mrmkt.command.delete_trigger import DeleteTrigger
from mrmkt.command.list_trigger import ListTriggers
from mrmkt.command.remove_triggerset import RemoveTriggerFromSet
from mrmkt.command.show_trigger import ShowTrigger
from mrmkt.command.triggers_common import (
    TRIGGER_COLUMNS,
    _default_trigger_name,
    _render_triggers_csv,
)
from mrmkt.command.triggersets_common import _default_set_name
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import Trigger

scenarios(
    "features/cli/add_trigger_to_set.feature",
    "features/cli/add_trigger_to_set_repository_release.feature",
    "features/cli/create_trigger.feature",
    "features/cli/create_triggerset.feature",
    "features/cli/delete_trigger.feature",
    "features/cli/list_triggers.feature",
    "features/cli/remove_trigger_from_set.feature",
    "features/cli/show_trigger.feature",
    "features/command/add_trigger_to_set.feature",
    "features/command/create_trigger.feature",
    "features/command/create_triggerset.feature",
    "features/command/delete_trigger.feature",
    "features/command/list_triggers.feature",
    "features/command/remove_trigger_from_set.feature",
    "features/command/show_trigger.feature",
)


@pytest.fixture
def trigger_context():
    context = SimpleNamespace(
        result=None,
        cli_result=None,
        failed=False,
        error="",
        name_generator=None,
        generated_trigger_name=None,
        generated_trigger_set_name=None,
        repository_closes=0,
    )
    return context


@given("the trigger catalog contains these symbols:")
def trigger_catalog_contains_symbols(financial_repository, datatable):
    headers = [str(header) for header in datatable[0]]
    for row in datatable[1:]:
        values = dict(zip(headers, row, strict=True))
        financial_repository.add_ticker(
            Ticker(
                ticker=values["symbol"],
                exchange=values["exchange"],
                type=values["type"],
            )
        )


@given(parsers.parse('trigger "{name}" exists'))
def trigger_exists(financial_repository, name):
    financial_repository.add_trigger(
        Trigger(
            id=None,
            name=name,
            symbol="AAA",
            signal="risk-range",
            operator="crossing-down",
            value=None,
            frequency="once_per_rearm",
            expires_at=None,
            message="",
            enabled=True,
        )
    )


@given(parsers.parse('trigger set "{name}" exists'))
def trigger_set_exists(financial_repository, name):
    financial_repository.create_set(name)


@given(parsers.parse('trigger "{trigger}" is in set "{set_name}"'))
def trigger_is_in_set(financial_repository, trigger, set_name):
    financial_repository.add_to_set(set_name, trigger)


@given(parsers.parse('the generated trigger name is "{name}"'))
def generated_trigger_name_is(trigger_context, name):
    trigger_context.generated_trigger_name = name


@given(parsers.parse('the generated trigger set name is "{name}"'))
def generated_trigger_set_name_is(trigger_context, name):
    trigger_context.generated_trigger_set_name = name


@given(parsers.parse('the next trigger name is "{name}"'))
def next_trigger_name_is(trigger_context, name):
    trigger_context.name_generator = lambda: name


@given(parsers.parse('trigger "{name}" is disabled in the store'))
def disable_trigger_in_store(financial_repository, name):
    matches = [
        item for item in financial_repository.list_triggers() if item.name == name
    ]
    assert_that(matches, has_length(1))
    trigger = matches[0]
    assert_that(trigger.id, not_none())
    trigger_id = cast(int, trigger.id)
    assert_that(financial_repository.set_trigger_enabled(trigger_id, False), is_(True))


@when(parsers.parse('I execute "{command}"'))
def execute_cli_command(trigger_context, command, financial_repository):
    args = split(command)
    trigger_name = trigger_context.generated_trigger_name
    trigger_set_name = trigger_context.generated_trigger_set_name

    def release_repository() -> None:
        trigger_context.repository_closes += 1

    deps = cli_dependencies_for_testing(
        repository=financial_repository,
        repository_release=release_repository,
        trigger_name_generator=(
            (lambda: trigger_name)
            if trigger_name is not None
            else _default_trigger_name
        ),
        triggerset_name_generator=(
            (lambda: trigger_set_name)
            if trigger_set_name is not None
            else _default_set_name
        ),
    )
    trigger_context.cli_result = CliRunner().invoke(
        cli.app, args[1:], obj=deps, env={"COLUMNS": "80"}
    )


def _table_options(datatable):
    return {str(row[0]): str(row[1]) for row in datatable[1:]}


def _create_kwargs(options):
    kwargs = {
        "name": options.get("name"),
        "symbol": options["symbol"],
        "signal": options.get("signal", "risk-range"),
        "operator": options.get("operator", "crossing-down"),
        "value": float(options["value"]) if "value" in options else None,
        "frequency": options.get("frequency", "once_per_rearm"),
        "expires": options.get("expires"),
        "message": options.get("message", ""),
    }
    return kwargs


def _with_generator(context, command_type, financial_repository):
    kwargs = {}
    if context.name_generator is not None:
        kwargs["name_generator"] = context.name_generator
    return command_type(financial_repository, **kwargs)


def _invoke(context, command, *args, **kwargs):
    context.result = None
    context.cli_result = None
    context.failed = False
    context.error = ""
    try:
        context.result = command.execute(*args, **kwargs)
    except ValueError as error:
        context.failed = True
        context.error = str(error)


@when("I create a trigger with:")
def create_trigger_command(trigger_context, datatable, financial_repository):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "value"]))
    command = _with_generator(trigger_context, CreateTrigger, financial_repository)
    _invoke(trigger_context, command, **_create_kwargs(_table_options(datatable)))


@when(parsers.parse('I show trigger "{name}"'))
def show_trigger_command(trigger_context, name, financial_repository):
    _invoke(trigger_context, ShowTrigger(financial_repository), name)


@when("I list triggers")
def list_triggers_command(trigger_context, financial_repository):
    _invoke(
        trigger_context,
        ListTriggers(financial_repository),
        enabled_only=False,
    )


@when("I list enabled triggers")
def list_enabled_triggers_command(trigger_context, financial_repository):
    _invoke(
        trigger_context,
        ListTriggers(financial_repository),
        enabled_only=True,
    )


@when(parsers.parse('I delete trigger "{name}"'))
def delete_trigger_command(trigger_context, name, financial_repository):
    _invoke(trigger_context, DeleteTrigger(financial_repository), name)


@when(parsers.parse('I create trigger set "{name}"'))
def create_trigger_set_command(trigger_context, name, financial_repository):
    _invoke(trigger_context, CreateTriggerSet(financial_repository), name)


@when("I create a trigger set with no name")
def create_default_trigger_set_command(trigger_context, financial_repository):
    _invoke(
        trigger_context,
        _with_generator(trigger_context, CreateTriggerSet, financial_repository),
        None,
    )


@when(parsers.parse('I add trigger "{trigger}" to set "{set_name}"'))
def add_trigger_to_set_command(
    trigger_context, trigger, set_name, financial_repository
):
    _invoke(
        trigger_context,
        AddTriggerToSet(financial_repository),
        set_name,
        trigger,
    )


@when(parsers.parse('the trigger "{trigger}" is added to triggerset "{set_name}"'))
def add_trigger_to_set_with_errors(
    trigger_context, trigger, set_name, financial_repository
):
    _invoke(
        trigger_context,
        AddTriggerToSet(financial_repository),
        set_name,
        trigger,
    )


@when(parsers.parse('I remove trigger "{trigger}" from set "{set_name}"'))
def remove_trigger_from_set_command(
    trigger_context, trigger, set_name, financial_repository
):
    _invoke(
        trigger_context,
        RemoveTriggerFromSet(financial_repository),
        set_name,
        trigger,
    )


@then("the command succeeds")
def command_succeeds(trigger_context):
    if trigger_context.cli_result is not None:
        assert_that(trigger_context.cli_result.exit_code, equal_to(0))
    else:
        assert_that(trigger_context.failed, is_(False), trigger_context.error)


@then("the command fails")
def cli_command_fails(trigger_context):
    assert_that(trigger_context.cli_result, not_none())
    assert_that(trigger_context.cli_result.exit_code, greater_than(0))


@then("the command fails with errors:")
def command_fails_with_errors(trigger_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "message"]))
    assert_that(trigger_context.failed, is_(True), "expected the command to fail")
    for row in datatable[1:]:
        field, message = str(row[0]), str(row[1])
        assert_that(trigger_context.error, contains_string(field))
        assert_that(trigger_context.error, contains_string(message))


@then("the console displays:")
def console_output_is_exactly(trigger_context, docstring):
    assert_that(trigger_context.cli_result, not_none())
    assert_that(
        trigger_context.cli_result.output,
        equal_to(f"{docstring}\n"),
    )


@then("the repository is released")
def repository_was_released_once(trigger_context):
    assert_that(trigger_context.repository_closes, equal_to(1))


@then(parsers.parse('the trigger is named "{name}"'))
def trigger_is_named(trigger_context, name):
    assert_that(trigger_context.result.name, equal_to(name))


@then(parsers.parse('the result is "{text}"'))
def result_is(trigger_context, text):
    assert_that(str(trigger_context.result), equal_to(text))


@then(parsers.parse('the trigger "{name}" has:'))
def trigger_has(trigger_context, name, datatable):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "value"]))
    aliases = {"expires": "expires_at"}
    expected = {
        aliases.get(str(row[0]), str(row[0])): str(row[1]) for row in datatable[1:]
    }
    result = trigger_context.result
    if isinstance(result, list):
        matches = [item for item in result if item.name == name]
        assert_that(matches, has_length(1))
        trigger = matches[0]
    else:
        assert_that(result.name, equal_to(name))
        trigger = result
    rendered = _render_triggers_csv([trigger]).splitlines()[-1]
    actual = dict(zip(TRIGGER_COLUMNS, rendered.split(","), strict=True))
    assert_that(set(actual).issuperset(expected), is_(True))
    for field, value in expected.items():
        assert_that(actual[field], equal_to(value))


@then(parsers.parse('trigger "{name}" is gone'))
def trigger_is_gone(trigger_context, name, financial_repository):
    assert_that(
        [
            item
            for item in financial_repository.list_triggers()
            if item.name == name
        ],
        equal_to([]),
    )


@then(parsers.parse('trigger "{name}" is not listed'))
def trigger_not_listed(trigger_context, name):
    result = trigger_context.result
    assert_that(result, instance_of(list))
    assert_that(
        [item for item in result if item.name == name],
        equal_to([]),
    )


@then(parsers.parse('set "{set_name}" contains "{trigger}"'))
def set_contains_trigger(financial_repository, set_name, trigger):
    assert_that(financial_repository.list_set_members(set_name), has_item(trigger))


@then(parsers.parse('set "{set_name}" is empty'))
def set_is_empty(set_name, financial_repository):
    assert_that(financial_repository.list_set_members(set_name), has_length(0))
