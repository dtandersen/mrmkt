"""BDD coverage for trigger and trigger-set commands and CLI commands."""

from shlex import split
from types import SimpleNamespace

import pytest
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
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
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
        local=InMemoryFinancialRepository(),
        result=None,
        cli_result=None,
        failed=False,
        error="",
        name_generator=None,
        generated_trigger_name=None,
        generated_trigger_set_name=None,
        repository_closes=0,
        repository_factory=None,
    )

    def repository_factory():
        def close_repository() -> None:
            context.repository_closes += 1

        return context.local, close_repository

    context.repository_factory = repository_factory
    return context


@given("the trigger catalog contains these symbols:")
def trigger_catalog_contains_symbols(trigger_context, datatable):
    headers = [str(header) for header in datatable[0]]
    for row in datatable[1:]:
        values = dict(zip(headers, row, strict=True))
        trigger_context.local.add_ticker(
            Ticker(
                ticker=values["symbol"],
                exchange=values["exchange"],
                type=values["type"],
            )
        )


@given(parsers.parse('trigger "{name}" exists'))
def trigger_exists(trigger_context, name):
    trigger_context.local.add_trigger(
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
def trigger_set_exists(trigger_context, name):
    trigger_context.local.create_set(name)


@given(parsers.parse('trigger "{trigger}" is in set "{set_name}"'))
def trigger_is_in_set(trigger_context, trigger, set_name):
    trigger_context.local.add_to_set(set_name, trigger)


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
def disable_trigger_in_store(trigger_context, name):
    trigger = next(
        (item for item in trigger_context.local.list_triggers() if item.name == name),
        None,
    )
    assert trigger is not None and trigger.id is not None
    assert trigger_context.local.set_trigger_enabled(trigger.id, False)


@when(parsers.parse('I execute "{command}"'))
def execute_cli_command(trigger_context, command):
    args = split(command)
    trigger_name = trigger_context.generated_trigger_name
    trigger_set_name = trigger_context.generated_trigger_set_name
    deps = cli_dependencies_for_testing(
        repository_factory=trigger_context.repository_factory,
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


def _with_generator(context, command_type):
    kwargs = {}
    if context.name_generator is not None:
        kwargs["name_generator"] = context.name_generator
    return command_type(context.local, **kwargs)


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
def create_trigger_command(trigger_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert headers == ["field", "value"]
    command = _with_generator(trigger_context, CreateTrigger)
    _invoke(trigger_context, command, **_create_kwargs(_table_options(datatable)))


@when(parsers.parse('I show trigger "{name}"'))
def show_trigger_command(trigger_context, name):
    _invoke(trigger_context, ShowTrigger(trigger_context.local), name)


@when("I list triggers")
def list_triggers_command(trigger_context):
    _invoke(
        trigger_context,
        ListTriggers(trigger_context.local),
        enabled_only=False,
    )


@when("I list enabled triggers")
def list_enabled_triggers_command(trigger_context):
    _invoke(
        trigger_context,
        ListTriggers(trigger_context.local),
        enabled_only=True,
    )


@when(parsers.parse('I delete trigger "{name}"'))
def delete_trigger_command(trigger_context, name):
    _invoke(trigger_context, DeleteTrigger(trigger_context.local), name)


@when(parsers.parse('I create trigger set "{name}"'))
def create_trigger_set_command(trigger_context, name):
    _invoke(trigger_context, CreateTriggerSet(trigger_context.local), name)


@when("I create a trigger set with no name")
def create_default_trigger_set_command(trigger_context):
    _invoke(
        trigger_context,
        _with_generator(trigger_context, CreateTriggerSet),
        None,
    )


@when(parsers.parse('I add trigger "{trigger}" to set "{set_name}"'))
def add_trigger_to_set_command(trigger_context, trigger, set_name):
    _invoke(
        trigger_context,
        AddTriggerToSet(trigger_context.local),
        set_name,
        trigger,
    )


@when(parsers.parse('the trigger "{trigger}" is added to triggerset "{set_name}"'))
def add_trigger_to_set_with_errors(trigger_context, trigger, set_name):
    _invoke(
        trigger_context,
        AddTriggerToSet(trigger_context.local),
        set_name,
        trigger,
    )


@when(parsers.parse('I remove trigger "{trigger}" from set "{set_name}"'))
def remove_trigger_from_set_command(trigger_context, trigger, set_name):
    _invoke(
        trigger_context,
        RemoveTriggerFromSet(trigger_context.local),
        set_name,
        trigger,
    )


@then("the command succeeds")
def command_succeeds(trigger_context):
    if trigger_context.cli_result is not None:
        assert trigger_context.cli_result.exit_code == 0, trigger_context.cli_result.output
    else:
        assert not trigger_context.failed, trigger_context.error


@then("the command fails")
def cli_command_fails(trigger_context):
    assert trigger_context.cli_result is not None
    assert trigger_context.cli_result.exit_code != 0, trigger_context.cli_result.output


@then("the command fails with errors:")
def command_fails_with_errors(trigger_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert headers == ["field", "message"]
    assert trigger_context.failed, "expected the command to fail"
    for row in datatable[1:]:
        field, message = str(row[0]), str(row[1])
        assert field in trigger_context.error, (field, trigger_context.error)
        assert message in trigger_context.error, (
            field,
            message,
            trigger_context.error,
        )


@then("the console displays:")
def console_output_is_exactly(trigger_context, docstring):
    assert trigger_context.cli_result is not None
    assert trigger_context.cli_result.output == f"{docstring}\n", (
        trigger_context.cli_result.output,
    )


@then("the repository is released")
def repository_was_released_once(trigger_context):
    assert trigger_context.repository_closes == 1, trigger_context.repository_closes


@then(parsers.parse('the trigger is named "{name}"'))
def trigger_is_named(trigger_context, name):
    assert trigger_context.result.name == name


@then(parsers.parse('the result is "{text}"'))
def result_is(trigger_context, text):
    assert str(trigger_context.result) == text


@then(parsers.parse('the trigger "{name}" has:'))
def trigger_has(trigger_context, name, datatable):
    headers = [str(header) for header in datatable[0]]
    assert headers == ["field", "value"]
    aliases = {"expires": "expires_at"}
    expected = {
        aliases.get(str(row[0]), str(row[0])): str(row[1]) for row in datatable[1:]
    }
    result = trigger_context.result
    if isinstance(result, list):
        matches = [item for item in result if item.name == name]
        assert len(matches) == 1, [item.name for item in result]
        trigger = matches[0]
    else:
        assert result.name == name
        trigger = result
    rendered = _render_triggers_csv([trigger]).splitlines()[-1]
    actual = dict(zip(TRIGGER_COLUMNS, rendered.split(","), strict=True))
    assert set(expected) <= set(actual), (expected, actual)
    for field, value in expected.items():
        assert actual[field] == value, (field, actual)


@then(parsers.parse('trigger "{name}" is gone'))
def trigger_is_gone(trigger_context, name):
    assert [item for item in trigger_context.local.list_triggers() if item.name == name] == []


@then(parsers.parse('trigger "{name}" is not listed'))
def trigger_not_listed(trigger_context, name):
    result = trigger_context.result
    assert isinstance(result, list)
    assert [item for item in result if item.name == name] == []


@then(parsers.parse('set "{set_name}" contains "{trigger}"'))
def set_contains_trigger(trigger_context, set_name, trigger):
    assert trigger in trigger_context.local.list_set_members(set_name)


@then(parsers.parse('set "{set_name}" is empty'))
def set_is_empty(trigger_context, set_name):
    assert trigger_context.local.list_set_members(set_name) == []
