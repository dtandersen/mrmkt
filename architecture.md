# Architecture

Onion architecture

# Libraries

- typer
- python-bdd + pytest
- vectorbt - backtesting engine

# Project Layout

|- src
|  |- command - commands
|  |- entity - entities
|  |- repo - db repository interfaces
|  |  |- ext - db repository implementation
|  |- indicator - built-in indicators
|  |- cli.py - mrmkt cli (typer)
|- tests
   |- features - bdd features
      |- cli - mrmkt cli features
      |- command - command features

# Testing

Project uses python-bdd + pytest. BDD features are preferred.

Tests target entrypoints, i.e. commands and mrmkt cli.

mrmkt cli tests are thin and verify arguments and passed correctly to the underlying command.

