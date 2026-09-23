Feature: Screener command paths
  As a MrMkt operator
  I want screen, signals, and freshness commands over tagged universes
  So that discovery is repeatable from stored bars

  Scenario: Screen ranks a tag universe as a deterministic CSV
    Given the screener catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | BBB    | NASDAQ   | us_equity |
    And each screener symbol has a 250-bar climb tagged universe
    When I execute "mrmkt screen --tag universe --top 2"
    Then the command succeeds
    And the output mentions "rank,symbol,last_date"
    And the output mentions "AAA"

  Scenario: Screen honors as-of for metrics and vintage
    Given the screener catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each screener symbol has a 250-bar climb tagged universe
    When I execute "mrmkt screen --tag universe --as-of 2022-12-01"
    Then the command succeeds
    And the output mentions "as_of=2022-12-01"
    And the output mentions "data_vintage=2022-12-01"

  Scenario: Signals current lists per-symbol status
    Given the screener catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each screener symbol has a 250-bar climb tagged universe
    When I execute "mrmkt signals current --tag universe --strategy sma-cross"
    Then the command succeeds
    And the output mentions "symbol,signal_date"
    And the output mentions "AAA"

  Scenario: Prices freshness reports quality flags
    Given the screener catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each screener symbol has a 250-bar climb tagged universe
    When I execute "mrmkt prices freshness --tag universe --lookback-days 400"
    Then the command succeeds
    And the output mentions "symbol,n_bars"
    And the output mentions "AAA"
