"""Feature CLI commands (thin wrappers around feature commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.create_feature import CreateFeatureRequest
from mrmkt.command.delete_feature import DeleteFeatureRequest
from mrmkt.command.list_features import ListFeaturesRequest
from mrmkt.command.show_feature import ShowFeatureRequest
from mrmkt.entity.feature import Feature

feature_app = typer.Typer(no_args_is_help=True, help="Store and read computed features")


def _format_value(feature: Feature) -> str:
    if feature.value_num is not None:
        return f"{feature.value_num:g}"
    return feature.value_text or ""


@feature_app.command("create")
def create_feature(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Symbol owning the feature"),
    assignment: str = typer.Argument(..., help="Feature assignment (name=value)"),
    date: str | None = typer.Option(
        None, "--date", help="Bar date (defaults to today)"
    ),
) -> None:
    """Store one computed feature value."""
    handle(
        ctx,
        lambda factory: factory.create_feature().execute(
            CreateFeatureRequest(symbol=symbol, assignment=assignment, date=date)
        ),
        lambda created: typer.echo(
            f"{created.symbol} {created.feature}={_format_value(created)} "
            f"{created.date.isoformat()}"
        ),
    )


@feature_app.command("delete")
def delete_feature(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Symbol owning the feature"),
    name: str = typer.Argument(..., help="Feature name"),
) -> None:
    """Delete all stored dates for one symbol+feature."""
    handle(
        ctx,
        lambda factory: factory.delete_feature().execute(
            DeleteFeatureRequest(symbol=symbol, name=name)
        ),
        lambda removed: typer.echo(
            f"Deleted {removed} row{'s' if removed != 1 else ''}."
        ),
    )


@feature_app.command("list")
def list_features(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Symbol owning the features"),
) -> None:
    """List stored features for one symbol as a deterministic table."""
    handle(
        ctx,
        lambda factory: factory.list_features().execute(
            ListFeaturesRequest(symbol=symbol)
        ),
        _echo_feature_list,
    )


def _echo_feature_list(rows) -> None:
    if not rows:
        typer.echo("No features found.")
        return
    typer.echo("SYMBOL | DATE | FEATURE | VALUE")
    for row in rows:
        typer.echo(
            f"{row.symbol} | {row.date.isoformat()} | {row.feature} | {_format_value(row)}"
        )


@feature_app.command("show")
def show_feature(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Symbol owning the feature"),
    name: str = typer.Argument(..., help="Feature name"),
) -> None:
    """Show the latest stored value for one symbol+feature."""
    handle(
        ctx,
        lambda factory: factory.show_feature().execute(
            ShowFeatureRequest(symbol=symbol, name=name)
        ),
        lambda row: typer.echo(
            f"{row.symbol} | {row.date.isoformat()} | {row.feature} | {_format_value(row)}"
        ),
    )
