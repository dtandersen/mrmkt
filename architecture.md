# Architecture

Onion architecture

Layers (outer to inner): cli -> command -> repo / entity, with ext + common as outer implementations.

# Libraries

- typer
- pytest-bdd + pytest
- vectorbt - backtesting engine

# Terminology

- Command - Command using the command pattern
- CLI Command - Typer command that invokes a command

# Boundaries

## Commands

Forbidden imports:

- `mrmkt.ext`
- `mrmkt.cli`
- `typer`

Commands may depend on repository interfaces from `mrmkt.repo`, passed as collaborators.

## CLI Commands

Forbidden imports:

- `mrmkt.repo`
- `mrmkt.ext`

CLI Commands invoke Commands; dependency construction belongs in the composition root.

# Project Layout

|- src
|  |- command - commands (called by cli/future rest api)
|  |  |- verb_noun.py
|  |  |- create_trigger.py
|  |  |- show_trigger.py
|  |  |- etc
|  |- cli
|  |  |- trigger.py
|  |  |- triggerset.py
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
      |  |- create_trigger.feature
      |  |- symbol_list.feature
         |- etc

# Commands

Commands are the basic building block of the application and represent a single use case.

Commands are named VerbNoun, e.g. AddTrigger.

Commands accept collaborators, such as repositories, via constructor arguments.

Commands perform validation and return their status, result, and a list of errors.


```python
# example command
class ImportSymbols(Command[ImportSymbolsRequest, ImportSymbolsResult]):
    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
      ...

    def execute(self, request: ImportSymbolsRequest) -> ImportSymbolsResult:
      if request.provider.lower() != "alpaca":
          return ImportSymbolsResult.invalid_data([...])
      ...
      return ImportSymbolsResult.success(imported_count)
```

# CLI Commands

CLI commands are thin wrappers around commands.

CLI commands do not use repositories.

CLI commands do not perform validation.

Create commands using the command factory in Typer ctx.

```python
# Example CLI command
@symbols_app.command("import")
def import_symbols(
   ctx: typer.Context,
   provider: str = typer.Option(..., "--provider", help="Symbol source (currently: alpaca)"),
) -> None:
   handle(
       ctx,
       lambda factory: factory.import_symbols().execute(
           ImportSymbolsRequest(provider=provider)
       ),
       lambda count: typer.echo(f"Imported {count} newly imported symbols."),
   )
```

## Verbs

- create / delete - resources
- import
- list
- add / remove - lists
- show
- run

# Testing

Use pytest-bdd + pytest.

BDD features are preferred to pytests.

BDD features must be readable and make it clear what is being tested.

Tests target *entrypoints*, i.e. commands and mrmkt cli. Repositories and API gateways are also tested if they connect to external services.

Each command and cli command is tested.

Avoid brittle internal structure tests to allow it to evolve.

Do not use mocks or monkeypatch with the exception of requests_mock. Use fakes and stubs to mimic the behavior of the interface.

See [TDD, Where Did It All Go Wrong (Ian Cooper)](https://www.youtube.com/watch?v=EZ05e7EMOLM).

`mrmkt` cli tests are thin and verify arguments are passed correctly to the underlying command.

Use PyHamcrest for assertions.
