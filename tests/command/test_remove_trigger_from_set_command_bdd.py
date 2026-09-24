"""BDD coverage for the RemoveTriggerFromSet command, driven directly (no CLI, no patching)."""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from steps.trigger_steps import (
    command_fails_with_errors,
    command_remove_from_set,
    command_succeeds,
    set_is_empty,
    trigger_exists,
    trigger_in_set,
    trigger_set_exists,
)

given(parsers.parse('trigger "{name}" exists'))(trigger_exists)
given(parsers.parse('trigger set "{name}" exists'))(trigger_set_exists)
given(parsers.parse('trigger "{trigger}" is in set "{set_name}"'))(trigger_in_set)
when(parsers.parse('I remove trigger "{trigger}" from set "{set_name}"'))(
    command_remove_from_set
)
then("the command succeeds")(command_succeeds)
then("the command fails with errors:")(command_fails_with_errors)
then(parsers.parse('set "{set_name}" is empty'))(set_is_empty)

FEATURE = Path(__file__).parent.parent / "features" / "command" / "remove_trigger_from_set.feature"
scenarios(str(FEATURE))
