"""BDD coverage for the AddTriggerToSet command, driven directly (no CLI, no patching)."""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from steps.trigger_steps import (
    command_add_to_set,
    command_fails_with_errors,
    command_succeeds,
    set_contains_trigger,
    trigger_exists,
    trigger_set_exists,
)

given(parsers.parse('trigger "{name}" exists'))(trigger_exists)
given(parsers.parse('trigger set "{name}" exists'))(trigger_set_exists)
when(parsers.parse('I add trigger "{trigger}" to set "{set_name}"'))(
    command_add_to_set
)
then("the command succeeds")(command_succeeds)
then("the command fails with errors:")(command_fails_with_errors)
then(parsers.parse('set "{set_name}" contains "{trigger}"'))(set_contains_trigger)

FEATURE = Path(__file__).parent.parent / "features" / "command" / "add_trigger_to_set.feature"
scenarios(str(FEATURE))
