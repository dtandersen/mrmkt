"""BDD coverage for the CreateTrigger command, driven directly (no CLI, no patching)."""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from steps.trigger_steps import (
    command_create_trigger,
    command_fails_with_errors,
    command_succeeds,
    next_trigger_name_is,
    trigger_has,
    trigger_is_named,
)

given(parsers.parse('the next trigger name is "{name}"'))(next_trigger_name_is)
when("I create a trigger with:")(command_create_trigger)
then("the command succeeds")(command_succeeds)
then("the command fails with errors:")(command_fails_with_errors)
then(parsers.parse('the trigger is named "{name}"'))(trigger_is_named)
then(parsers.parse('the trigger "{name}" has:'))(trigger_has)

FEATURE = (
    Path(__file__).parent.parent / "features" / "command" / "create_trigger.feature"
)
scenarios(str(FEATURE))
