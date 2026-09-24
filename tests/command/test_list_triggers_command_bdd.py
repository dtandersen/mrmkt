"""BDD coverage for the ListTriggers command, driven directly (no CLI, no patching)."""

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from steps.trigger_steps import (
    command_list_enabled_triggers,
    command_list_triggers,
    command_succeeds,
    disable_trigger_in_store,
    trigger_exists,
    trigger_has,
    trigger_not_listed,
)

given(parsers.parse('trigger "{name}" exists'))(trigger_exists)
when("I list triggers")(command_list_triggers)
when("I list enabled triggers")(command_list_enabled_triggers)
given(parsers.parse('trigger "{name}" is disabled in the store'))(
    disable_trigger_in_store
)
then("the command succeeds")(command_succeeds)
then(parsers.parse('the trigger "{name}" has:'))(trigger_has)
then(parsers.parse('trigger "{name}" is not listed'))(trigger_not_listed)

FEATURE = Path(__file__).parent.parent / "features" / "command" / "list_triggers.feature"
scenarios(str(FEATURE))
