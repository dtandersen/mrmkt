"""BDD coverage for the trigger show CLI path."""

from pathlib import Path

from cli_steps.trigger_cli_steps import (
    execute_trigger_command,
    trigger_command_fails,
    trigger_console_output_is_exactly,
)
from pytest_bdd import parsers, scenarios, then, when

when(parsers.parse('I execute "{command}"'))(execute_trigger_command)
then("the command fails")(trigger_command_fails)
then("the console displays:")(trigger_console_output_is_exactly)

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "show_trigger.feature"
scenarios(str(FEATURE))
