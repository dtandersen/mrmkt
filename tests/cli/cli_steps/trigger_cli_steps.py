"""Shared step implementations for trigger CLI BDD.

Plain (undecorated) step functions reused by every trigger CLI feature
runner in this directory — each runner explicitly imports the functions
its feature uses and applies the pytest-bdd decorators itself, so the
steps register in the runner's own module namespace. The shared
``trigger_context`` fixture lives in ``tests/cli/conftest.py``. Every
invocation goes through ``CliRunner`` with the composition-root
dependencies (in-memory repository factory, pinned name generators, and
the add-trigger-to-set command factory) injected as the Typer ``obj``;
scenarios assert exit codes plus console output.
"""

from shlex import split

from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.command.triggersets_common import _default_set_name
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import Trigger


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


def trigger_catalog_contains_symbols(trigger_context, datatable):
    for row in _table_rows(datatable):
        trigger_context.local.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


def cli_trigger_exists(trigger_context, name):
    """Seed a stored trigger directly (no CLI invocation)."""
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


def cli_trigger_set_exists(trigger_context, name):
    """Seed an empty trigger set directly (no CLI invocation)."""
    trigger_context.local.create_set(name)


def cli_trigger_in_set(trigger_context, trigger, set_name):
    """Seed set membership directly (no CLI invocation)."""
    trigger_context.local.add_to_set(set_name, trigger)


def cli_generated_trigger_name_is(trigger_context, name):
    """Record the pinned trigger name; the execute step injects it."""
    trigger_context.generated_trigger_name = name


def cli_generated_trigger_set_name_is(trigger_context, name):
    """Record the pinned trigger-set name; the execute step injects it."""
    trigger_context.generated_trigger_set_name = name


def execute_trigger_command(trigger_context, command):
    args = split(command)
    trigger_name = trigger_context.generated_trigger_name
    set_name = trigger_context.generated_trigger_set_name
    deps = cli_dependencies_for_testing(
        repository_factory=trigger_context.repository_factory,
        trigger_name_generator=(
            (lambda: trigger_name)
            if trigger_name is not None
            else _default_trigger_name
        ),
        triggerset_name_generator=(
            (lambda: set_name) if set_name is not None else _default_set_name
        ),
    )
    trigger_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=deps, env={"COLUMNS": "80"}
    )


def trigger_command_succeeds(trigger_context):
    assert trigger_context.result.exit_code == 0, trigger_context.result.output


def trigger_command_fails(trigger_context):
    assert trigger_context.result.exit_code != 0, trigger_context.result.output


def trigger_console_output_is_exactly(trigger_context, docstring):
    assert trigger_context.result.output == f"{docstring}\n", (
        trigger_context.result.output,
    )


def trigger_repository_was_released_once(trigger_context):
    """Assert the CLI released the repository handed out by the injected factory."""
    assert trigger_context.repository_closes == 1, trigger_context.repository_closes
