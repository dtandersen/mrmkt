Feature: Ranges and watch command paths
  As a MrMkt operator
  I want ranges and watch over stored bars
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

  Scenario: Ranges rejects an unknown signal
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt ranges AAA --signal bogus"
    Then the command fails
    And the output mentions "unknown signal"

  Scenario: Watch dry-run replays stored lows and reports touches
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt watch AAA --dry-run --signal risk-range"
    Then the command succeeds
    And the output mentions "# dry-run: replaying stored daily lows"
    And the output mentions "would alert:"
    And the output mentions "TRIGGER"

  Scenario: Watch rejects a bad session policy
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt watch AAA --dry-run --session-policy bogus"
    Then the command fails
    And the output mentions "--session-policy must be regular or extended"

  Scenario: Watch rejects an unknown sink
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt watch AAA --dry-run --sink carrier-pigeon"
    Then the command fails
    And the output mentions "unknown sink"

  Scenario: Watch rejects an unknown signal
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar steady climb tagged universe
    When I execute "mrmkt watch AAA --dry-run --signal bogus"
    Then the command fails
    And the output mentions "unknown signal"

  Scenario: Watch replays stored triggers without touching sinks
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt watch --all-triggers --dry-run"
    Then the command succeeds
    And the output mentions "sinks not called"
    And the output mentions "would alert: "
    And the output mentions "AAA"

  Scenario: Watch dry-run scores only selected symbols
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | BBB    | NASDAQ   | us_equity |
    And AAA has a 60-bar climb with a dip
    And BBB has a 5-bar climb
    When I execute "mrmkt watch AAA BBB --dry-run"
    Then the command succeeds
    And the output mentions "AAA"
    And the output omits "BBB"

  Scenario: Watch rejects an unknown trigger id
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt watch --trigger-id 999 --dry-run"
    Then the command fails
    And the output mentions "no enabled trigger"
