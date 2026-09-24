# Architecture

Onion architecture

Layers (outer to inner): cli -> command -> repo / entity, with ext + common as outer implementations.

# Libraries

- typer
- pytest-bdd + pytest
- vectorbt - backtesting engine

# Project Layout

|- src
|  |- command - commands (called by cli/future rest api)
|  |  |- trigger_add.py
|  |  |- trigger_remove.py
|  |  |- etc
|  |- entity - entities (returned by repositories and gateways)
|  |- repo - repository interfaces
|  |- ext - repository/gateway implementations
|  |- common - shared impl (sql repo, clocks, config)
|  |- indicator - built-in indicators
|  |- backtest - strategies + portfolio simulation
|  |- models - research models
|  |- cli.py - mrmkt cli (typer)
|- tests
   |- features - BDD features
      |- cli - mrmkt cli BDD features (thin tests)
      |  |- trigger_create.feature
      |  |- symbol_list.feature
      |  |- etc
      |- command - command BDD features (extensive tests)
      |  |- trigger_create.feature
      |  |- symbol_list.feature
         |- etc

# Commands

Commands are the basic building block of the application and represent a single use case.

## Verbs

- add
- import
- list
- remove
- show
- run

# Testing

Use pytest-bdd + pytest.

BDD features are preferred to pytests.

BDD features must be readable and make it clear what is being tested.

Tests target *entrypoints*, i.e. commands and mrmkt cli. Repositories and API gateways are also tested if they connect to external services.

Each command and cli command is tested.

Avoid brittle internal structure tests to allow it to evolve.

Do not use mocks with the exception of requests_mock. Use fakes and stubs that mimic the behavior of the interface.

See [TDD, Where Did It All Go Wrong (Ian Cooper)](https://www.youtube.com/watch?v=EZ05e7EMOLM).

`mrmkt` cli tests are thin and verify arguments are passed correctly to the underlying command.

Use PyHamcrest for assertions.
