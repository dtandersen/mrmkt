"""Shared mapping from command results to CLI behavior."""

from collections.abc import Callable

import typer

from mrmkt.command.base import BaseResult
from mrmkt.composition import CommandFactory, resolve_cli_dependencies


def handle[T](
    ctx: typer.Context | None,
    run: Callable[[CommandFactory], BaseResult[T]],
    on_success: Callable[[T | None], None],
) -> None:
    """Resolve dependencies, run a command, and render or raise its outcome."""
    env = resolve_cli_dependencies(ctx)
    result_or_exit(run(env.command_factory), on_success)


def result_or_exit[T](
    result: BaseResult[T], on_success: Callable[[T | None], None]
) -> None:
    """Render a successful payload, or raise the CLI failure for a bad outcome.

    INVALID_DATA and NOT_FOUND are usage errors; anything else is a runtime
    failure reported on stderr.
    """
    if result.is_success():
        on_success(result.result)
        return
    if result.is_invalid_data() or result.is_not_found():
        raise typer.BadParameter("; ".join(result.errors))
    typer.echo("; ".join(result.errors) or result.status.name, err=True)
    raise typer.Exit(code=1)
