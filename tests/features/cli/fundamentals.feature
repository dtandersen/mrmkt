Feature: Import and show fundamentals from the CLI
  As a MrMkt operator
  I want thin CLI wrappers over the fundamentals commands
  So that imports and lookups run from the command line

  Scenario: Import fundamentals for selected symbols
    Given stored bars:
      | symbol | date       | close |
      | AAPL   | 2024-03-31 | 40    |
    And the fundamentals source serves "AAPL" with filing "2024-03-31" and caps "2024-04-01:50000"
    When I execute "mrmkt fundamentals import --provider tiingo AAPL"
    Then the command succeeds
    And the fundamentals source receives the symbols "AAPL"
    And the import reports 4 new fundamental rows

  Scenario: Import fundamentals for a tag universe
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    And stored bars:
      | symbol | date       | close |
      | AAPL   | 2024-03-31 | 40    |
    And the fundamentals source serves "AAPL" with filing "2024-03-31" and caps "2024-04-01:50000"
    When I execute "mrmkt fundamentals import --provider tiingo --tag sp500"
    Then the command succeeds
    And the fundamentals source receives the symbols "AAPL"
    And the import reports 4 new fundamental rows

  Scenario: Reject a missing selector before calling the source
    When I execute "mrmkt fundamentals import --provider tiingo"
    Then the command fails
    And the fundamentals source is not called

  Scenario: Show stored fundamentals
    Given stored fundamentals for "AAPL" on "2024-03-31"
    When I execute "mrmkt fundamentals show AAPL"
    Then the command succeeds
    And the output names "AAPL"

  Scenario: Show is case-insensitive and reports unknown symbols
    Given stored fundamentals for "AAPL" on "2024-03-31"
    When I execute "mrmkt fundamentals show aapl"
    Then the command succeeds
    And the output names "AAPL"
    When I execute "mrmkt fundamentals show ZZZ"
    Then the command fails
