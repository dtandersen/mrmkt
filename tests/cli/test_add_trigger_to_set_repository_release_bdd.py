"""BDD coverage for repository release on the triggerset add CLI path."""

from pathlib import Path

from cli_steps.trigger_cli_steps import (
    cli_trigger_exists,
    cli_trigger_set_exists,
    execute_trigger_command,
    trigger_command_fails,
    trigger_command_succeeds,
    trigger_repository_was_released_once,
)
from pytest_bdd import given, parsers, scenarios, then, when

given(parsers.parse('trigger "{name}" exists'))(cli_trigger_exists)
given(parsers.parse('trigger set "{name}" exists'))(cli_trigger_set_exists)
when(parsers.parse('I execute "{command}"'))(execute_trigger_command)
then("the command succeeds")(trigger_command_succeeds)
then("the command fails")(trigger_command_fails)
then("the repository is released")(trigger_repository_was_released_once)

FEATURE = (
    Path(__file__).parent.parent
    / "features"
    / "cli"
    / "add_trigger_to_set_repository_release.feature"
)
scenarios(str(FEATURE))
