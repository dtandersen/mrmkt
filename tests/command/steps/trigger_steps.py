"""Shared step implementations for trigger command BDD.

Plain (undecorated) step functions reused by every command feature runner
in this directory — each runner explicitly imports the functions its
feature uses and applies the pytest-bdd decorators itself, so the steps
register in the runner's own module namespace. The shared
``trigger_command_context`` fixture lives in ``tests/command/conftest.py``.
All scenarios run against the in-memory fake repository; no monkeypatching.
"""

from mrmkt.command.add_triggerset import AddTriggerToSet
from mrmkt.command.create_trigger import CreateTrigger
from mrmkt.command.create_triggerset import CreateTriggerSet
from mrmkt.command.delete_trigger import DeleteTrigger
from mrmkt.command.list_trigger import ListTriggers
from mrmkt.command.remove_triggerset import RemoveTriggerFromSet
from mrmkt.command.show_trigger import ShowTrigger
from mrmkt.command.triggers_common import TRIGGER_COLUMNS, _render_triggers_csv
from mrmkt.entity.trigger import Trigger


def trigger_exists(trigger_command_context, name):
    """Seed a stored trigger directly (no command invoked)."""
    trigger_command_context.local.add_trigger(
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


def trigger_set_exists(trigger_command_context, name):
    """Seed an empty trigger set directly (no command invoked)."""
    trigger_command_context.local.create_set(name)


def trigger_in_set(trigger_command_context, trigger, set_name):
    """Seed set membership directly (no command invoked)."""
    trigger_command_context.local.add_to_set(set_name, trigger)


def trigger_is_gone(trigger_command_context, name):
    result = trigger_command_context.local.list_triggers()
    assert [t for t in result if t.name == name] == []


def _table_options(datatable):
    return {str(row[0]): str(row[1]) for row in datatable[1:]}


def _invoke(context, command, *args, **kwargs):
    context.result = None
    context.failed = False
    context.error = ""
    try:
        context.result = command.execute(*args, **kwargs)
    except ValueError as error:
        context.failed = True
        context.error = str(error)


def _create_kwargs(options):
    kwargs = {"value": None, "message": ""}
    kwargs["name"] = options.get("name")
    kwargs["symbol"] = options["symbol"]
    kwargs["signal"] = options.get("signal", "risk-range")
    kwargs["operator"] = options.get("operator", "crossing-down")
    if "value" in options:
        kwargs["value"] = float(options["value"])
    kwargs["frequency"] = options.get("frequency", "once_per_rearm")
    if "expires" in options:
        kwargs["expires"] = options["expires"]
    else:
        kwargs["expires"] = None
    if "message" in options:
        kwargs["message"] = options["message"]
    return kwargs


def _with_generator(context, cls):
    kwargs = {}
    if context.name_generator is not None:
        kwargs["name_generator"] = context.name_generator
    return cls(context.local, **kwargs)


def next_trigger_name_is(trigger_command_context, name):
    trigger_command_context.name_generator = lambda: name


def command_create_trigger(trigger_command_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert headers == ["field", "value"]
    command = _with_generator(trigger_command_context, CreateTrigger)
    _invoke(
        trigger_command_context,
        command,
        **_create_kwargs(_table_options(datatable)),
    )


def command_show_trigger(trigger_command_context, name):
    _invoke(trigger_command_context, ShowTrigger(trigger_command_context.local), name)


def command_list_triggers(trigger_command_context):
    _invoke(
        trigger_command_context,
        ListTriggers(trigger_command_context.local),
        enabled_only=False,
    )


def command_list_enabled_triggers(trigger_command_context):
    _invoke(
        trigger_command_context,
        ListTriggers(trigger_command_context.local),
        enabled_only=True,
    )


def command_delete_trigger(trigger_command_context, name):
    _invoke(trigger_command_context, DeleteTrigger(trigger_command_context.local), name)


def command_create_set(trigger_command_context, name):
    _invoke(
        trigger_command_context, CreateTriggerSet(trigger_command_context.local), name
    )


def command_create_set_default(trigger_command_context):
    _invoke(
        trigger_command_context,
        _with_generator(trigger_command_context, CreateTriggerSet),
        None,
    )


def command_add_to_set(trigger_command_context, trigger, set_name):
    _invoke(
        trigger_command_context,
        AddTriggerToSet(trigger_command_context.local),
        set_name,
        trigger,
    )


def command_remove_from_set(trigger_command_context, trigger, set_name):
    _invoke(
        trigger_command_context,
        RemoveTriggerFromSet(trigger_command_context.local),
        set_name,
        trigger,
    )


def disable_trigger_in_store(trigger_command_context, name):
    trigger = next(
        (t for t in trigger_command_context.local.list_triggers() if t.name == name),
        None,
    )
    assert trigger is not None and trigger.id is not None
    assert trigger_command_context.local.set_trigger_enabled(trigger.id, False)


def command_succeeds(trigger_command_context):
    assert not trigger_command_context.failed, trigger_command_context.error


def command_fails_with_errors(trigger_command_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert headers == ["field", "message"]
    assert trigger_command_context.failed, "expected the command to fail"
    for row in datatable[1:]:
        field, message = str(row[0]), str(row[1])
        assert field in trigger_command_context.error, (
            field,
            trigger_command_context.error,
        )
        assert message in trigger_command_context.error, (
            field,
            message,
            trigger_command_context.error,
        )


def trigger_is_named(trigger_command_context, name):
    assert trigger_command_context.result.name == name


def result_is(trigger_command_context, text):
    assert str(trigger_command_context.result) == text


def result_starts_with(trigger_command_context, prefix):
    assert str(trigger_command_context.result).startswith(prefix)


def trigger_has(trigger_command_context, name, datatable):
    headers = [str(header) for header in datatable[0]]
    assert headers == ["field", "value"]
    aliases = {"expires": "expires_at"}
    expected = {
        aliases.get(str(row[0]), str(row[0])): str(row[1]) for row in datatable[1:]
    }
    result = trigger_command_context.result
    if isinstance(result, list):
        matches = [t for t in result if t.name == name]
        assert len(matches) == 1, [t.name for t in result]
        trigger = matches[0]
    else:
        assert result.name == name
        trigger = result
    rendered = _render_triggers_csv([trigger]).splitlines()[-1]
    actual = dict(zip(TRIGGER_COLUMNS, rendered.split(","), strict=True))
    assert set(expected) <= set(actual), (expected, actual)
    for field, value in expected.items():
        assert actual[field] == value, (field, actual)


def trigger_not_listed(trigger_command_context, name):
    result = trigger_command_context.result
    assert isinstance(result, list)
    assert [t for t in result if t.name == name] == []


def set_contains_trigger(trigger_command_context, set_name, trigger):
    assert trigger in trigger_command_context.local.list_set_members(set_name)


def set_is_empty(trigger_command_context, set_name):
    assert trigger_command_context.local.list_set_members(set_name) == []
