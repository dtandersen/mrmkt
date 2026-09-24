Feature: Technical screen use case
  As a MrMkt operator
  I want point-in-time technical ranking over a tag universe
  So that candidate discovery is repeatable from stored bars

  Scenario: A steady climber outranks a decliner
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.003 tagged "universe"
    And symbol "BBB" has a 250-bar climb at drift -0.002 tagged "universe"
    When I screen tag "universe"
    Then the screen succeeds with 2 ranked rows
    And "AAA" ranks above "BBB"

  Scenario: Metrics never look past as-of
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.002 tagged "universe"
    When I screen tag "universe" as of 30 bars before the last bar
    Then every row has last_date on or before as-of
    And data vintage equals as-of

  Scenario: Price floors exclude with a reason count
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.002 tagged "universe"
    When I screen tag "universe" with min-price 100000.0
    Then the screen succeeds with 0 ranked rows
    And exclusions report "min_price"

  Scenario: Repeats are deterministic
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.002 tagged "universe"
    When I screen tag "universe" twice
    Then both CSV renders are identical

  Scenario: Only technical-only mode exists
    Given a clean price catalog
    When I screen in mode "fundamental"
    Then the screen fails naming "technical-only"

  Scenario: Include and exclude tags combine
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.003 tagged "universe"
    And symbol "BBB" has a 250-bar climb at drift 0.001 tagged "universe"
    And symbol "CCC" has a 250-bar climb at drift 0.001 tagged "universe"
    And symbol "CCC" is also tagged "junk"
    When I screen tag "universe" excluding "junk"
    Then the screen succeeds with 2 ranked rows
    And the rows are exactly "AAA" and "BBB"

  Scenario: Vintage spans the full universe before top-n
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.003 tagged "universe"
    And symbol "BBB" has a 250-bar climb at drift 0.001 tagged "universe"
    When I screen tag "universe" with top 1
    Then data vintage equals the full-universe vintage

  Scenario: Short history is excluded with reason
    Given a clean price catalog
    And symbol "SHORT" has a 50-bar climb at drift 0.002 tagged "universe"
    When I screen tag "universe"
    Then the screen succeeds with 0 ranked rows
    And exclusions report "short_history"

  Scenario: Stale names stay unless gated
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.002 tagged "universe"
    When I screen tag "universe" with max stale days 5
    Then the CSV header echoes "max_stale_days=5"

  Scenario: Scores rank best first with symbol tiebreak
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.003 tagged "universe"
    And symbol "BBB" has a 250-bar climb at drift 0.001 tagged "universe"
    When I screen tag "universe"
    Then scores descend with symbol tiebreak

  Scenario: Membership vintage is current, never point-in-time
    Given a clean price catalog
    And symbol "AAA" has a 250-bar climb at drift 0.002 tagged "universe"
    When I screen tag "universe"
    Then the CSV header reports current membership vintage
