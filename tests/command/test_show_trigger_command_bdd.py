"""BDD coverage for the ShowTrigger command, driven directly (no CLI, no patching)."""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from steps.trigger_steps import (
    command_fails_with_errors,
    command_show_trigger,
    command_succeeds,
    trigger_exists,
    trigger_has,
)

given(parsers.parse('trigger "{name}" exists'))(trigger_exists)
when(parsers.parse('I show trigger "{name}"'))(command_show_trigger)
then("the command succeeds")(command_succeeds)
then("the command fails with errors:")(command_fails_with_errors)
then(parsers.parse('the trigger "{name}" has:'))(trigger_has)

FEATURE = Path(__file__).parent.parent / "features" / "command" / "show_trigger.feature"
scenarios(str(FEATURE))
