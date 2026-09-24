"""BDD coverage for the CreateTriggerSet command, driven directly (no CLI, no patching)."""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from steps.trigger_steps import (
    command_create_set,
    command_create_set_default,
    command_fails_with_errors,
    command_succeeds,
    next_trigger_name_is,
    result_is,
)

given(parsers.parse('the next trigger name is "{name}"'))(next_trigger_name_is)
when(parsers.parse('I create trigger set "{name}"'))(command_create_set)
when("I create a trigger set with no name")(command_create_set_default)
then("the command succeeds")(command_succeeds)
then("the command fails with errors:")(command_fails_with_errors)
then(parsers.parse('the result is "{text}"'))(result_is)

FEATURE = Path(__file__).parent.parent / "features" / "command" / "create_triggerset.feature"
scenarios(str(FEATURE))
