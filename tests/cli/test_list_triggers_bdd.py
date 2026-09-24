"""BDD coverage for the trigger list CLI path."""

from pathlib import Path

from cli_steps.trigger_cli_steps import (
    execute_trigger_command,
    trigger_catalog_contains_symbols,
    trigger_command_succeeds,
    trigger_console_output_is_exactly,
)
from pytest_bdd import given, parsers, scenarios, then, when

given("the trigger catalog contains these symbols:")(
    trigger_catalog_contains_symbols
)
when(parsers.parse('I execute "{command}"'))(execute_trigger_command)
then("the command succeeds")(trigger_command_succeeds)
then("the console displays:")(trigger_console_output_is_exactly)

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "list_triggers.feature"
scenarios(str(FEATURE))
