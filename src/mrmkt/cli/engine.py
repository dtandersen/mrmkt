"""Engine CLI commands (thin wrappers around engine commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.start_engine import StartEngineRequest

engine_app = typer.Typer(no_args_is_help=True, help="Start the realtime engine")


@engine_app.command("start")
def engine_start(
    ctx: typer.Context,
    subject: str = typer.Option(
        "subscribe.realtime.price",
        "--subject",
        help="Queue subject to attach to",
    ),
) -> None:
    """Start the engine; attaches to the queue's realtime price events."""
    handle(
        ctx,
        lambda factory: factory.start_engine().execute(
            StartEngineRequest(subject=subject)
        ),
        lambda _: None,
    )
