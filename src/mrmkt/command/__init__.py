"""mrmkt command entrypoints (called by cli/future rest api)."""

import typer

symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")
prices_app = typer.Typer(no_args_is_help=True, help="Import and list historical prices")
indicators_app = typer.Typer(no_args_is_help=True, help="Calculate indicators over stored prices")
backtest_app = typer.Typer(no_args_is_help=True, help="Backtest signal portfolios over stored prices")
signals_app = typer.Typer(no_args_is_help=True, help="Inspect current strategy signals over stored prices")
trigger_app = typer.Typer(no_args_is_help=True, help="Manage stored realtime alert triggers")
