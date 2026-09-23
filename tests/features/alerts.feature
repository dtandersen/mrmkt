Feature: Alerts command paths
  As a MrMkt operator
  I want alerts levels and watch over stored bars
  So that risk-range triggers are repeatable from the CLI

  Scenario: Levels prints a deterministic CSV for a tagged universe
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt alerts levels --tag universe"
    Then the command succeeds
    And the output mentions "# generator=mrmkt alerts levels"
    And the output mentions "symbol,as_of,close,range_low,range_high,n_bars"
    And the output mentions "AAA"

  Scenario: Levels honors as-of for range vintage
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt alerts levels --tag universe --as-of 2022-02-25"
    Then the command succeeds
    And the output mentions "as_of=2022-02-25"
    And the output mentions "AAA"

  Scenario: Levels requires symbols or a tag
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt alerts levels"
    Then the command fails
    And the output mentions "provide symbols or --tag"

  Scenario: Watch dry-run replays stored lows and reports touches
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt alerts watch AAA --dry-run"
    Then the command succeeds
    And the output mentions "# dry-run: replaying stored daily lows"
    And the output mentions "would alert:"
    And the output mentions "TRIGGER"

  Scenario: Watch rejects a bad session policy
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt alerts watch AAA --dry-run --session-policy bogus"
    Then the command fails
    And the output mentions "--session-policy must be regular or extended"

  Scenario: Watch rejects an unknown sink
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt alerts watch AAA --dry-run --sink carrier-pigeon"
    Then the command fails
    And the output mentions "unknown sink"
