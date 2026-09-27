Feature: Ranges command paths
  As a MrMkt operator
  I want ranges over stored bars
  So that risk-range triggers are repeatable from the CLI

  Scenario: Ranges prints a deterministic CSV for a tagged universe
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt ranges --tag universe"
    Then the command succeeds
    And the output mentions "# generator=mrmkt ranges"
    And the output mentions "symbol,as_of,close,range_low,range_high,n_bars"
    And the output mentions "AAA"

  Scenario: Ranges honors as-of for range vintage
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt ranges --tag universe --as-of 2022-02-25"
    Then the command succeeds
    And the output mentions "as_of=2022-02-25"
    And the output mentions "AAA"

  Scenario: Ranges requires symbols or a tag
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt ranges"
    Then the command fails
    And the output mentions "provide symbols or --tag"

  Scenario: Ranges rejects an invalid indicator
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt ranges AAA --indicator bogus!"
    Then the command fails
    And the output mentions "invalid indicator"
