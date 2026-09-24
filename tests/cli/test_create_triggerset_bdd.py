"""BDD coverage for the triggerset create CLI path."""

from pathlib import Path

from cli_steps.trigger_cli_steps import (
    cli_generated_trigger_set_name_is,
    execute_trigger_command,
    trigger_command_fails,
    trigger_command_succeeds,
    trigger_console_output_is_exactly,
)
from pytest_bdd import given, parsers, scenarios, then, when

given(parsers.parse('the generated trigger set name is "{name}"'))(
    cli_generated_trigger_set_name_is
)
when(parsers.parse('I execute "{command}"'))(execute_trigger_command)
then("the command succeeds")(trigger_command_succeeds)
then("the command fails")(trigger_command_fails)
then("the console displays:")(trigger_console_output_is_exactly)

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "create_triggerset.feature"
scenarios(str(FEATURE))
