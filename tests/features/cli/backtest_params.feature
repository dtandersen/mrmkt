Feature: Backtest strategy params
  As a MrMkt operator
  I want to pass strategy params as k=v pairs
  So that any strategy is tunable without new CLI flags

  Scenario: Unknown strategy names the valid choices
    When I execute "mrmkt backtest run AAPL --strategy nope"
    Then the command fails
    And the output mentions "unknown strategy"
    And the output mentions "buy-red"

  Scenario: Unknown param names the valid keys
    When I execute "mrmkt backtest run AAPL --params bogus=1"
    Then the command fails
    And the output mentions "unknown params"
    And the output mentions "width"

  Scenario: Malformed pair reports the expected shape
    When I execute "mrmkt backtest run AAPL --params width"
    Then the command fails
    And the output mentions "params must look like k=v,k2=v2"

  Scenario: Bad value names the param
    When I execute "mrmkt backtest run AAPL --params width=wide"
    Then the command fails
    And the output mentions "param width"

  Scenario: Blank params fall back to defaults
    When I execute "mrmkt backtest run AAPL --params ''"
    Then the command succeeds
    And the output mentions "No symbols with enough history"

  Scenario: Valid custom params flow through to the run
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    And the local price catalog contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
    When I execute "mrmkt backtest run AAPL --params width=1.0,use_vov=false"
    Then the command succeeds
    And the output mentions "No symbols with enough history"

  Scenario: Invalid param combination reports the rule
    When I execute "mrmkt backtest run AAPL --strategy sma-cross --params fast_period=200,slow_period=50"
    Then the command fails
    And the output mentions "require 1 <="
