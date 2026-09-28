Feature: Store and read computed features
  As a MrMkt operator
  I want to store named feature values per symbol and read them back
  So that screens can log point-in-time inputs for later validation

  Scenario: Create a numeric feature with an explicit date
    Given the ticker catalog contains:
      | symbol | exchange | type      |
      | SPY    | NASDAQ   | us_equity |
    When I create feature "rr15.low=760.42" for "SPY" on "2026-09-24"
    Then the command succeeds
    And the stored feature reads back as "SPY | 2026-09-24 | rr15.low | 760.42"

  Scenario: Create a text feature defaulting to today
    Given the ticker catalog contains:
      | symbol | exchange | type      |
      | SPY    | NASDAQ   | us_equity |
    And the fake clock says today is "2026-09-27"
    When I create feature "trend.state=up" for "SPY" with no date
    Then the command succeeds
    And the stored feature reads back as "SPY | 2026-09-27 | trend.state | up"

  Scenario: Reject a malformed assignment
    When I create feature "rr15.low" for "SPY" on "2026-09-24"
    Then the command fails with invalid data

  Scenario: Reject an unknown symbol
    When I create feature "rr15.low=1" for "ZZZ" on "2026-09-24"
    Then the command reports not found

  Scenario: Reject a duplicate key
    Given the ticker catalog contains:
      | symbol | exchange | type      |
      | SPY    | NASDAQ   | us_equity |
    And stored features:
      | symbol | exchange | feature  | date       | value |
      | SPY    | NASDAQ   | rr15.low | 2026-09-24 | 760.42 |
    When I create feature "rr15.low=761" for "SPY" on "2026-09-24"
    Then the command fails with invalid data

  Scenario: Show returns the latest date
    Given stored features:
      | symbol | exchange | feature  | date       | value  |
      | SPY    | NASDAQ   | rr15.low | 2026-09-23 | 755.10 |
      | SPY    | NASDAQ   | rr15.low | 2026-09-24 | 760.42 |
    When I show feature "rr15.low" for "SPY"
    Then the command succeeds
    And the shown feature reads back as "SPY | 2026-09-24 | rr15.low | 760.42"

  Scenario: Show reports a missing feature
    When I show feature "rr15.low" for "SPY"
    Then the command reports not found

  Scenario: List features in deterministic order
    Given stored features:
      | symbol | exchange | feature     | date       | value |
      | SPY    | NASDAQ   | rr15.high   | 2026-09-24 | 780.72 |
      | SPY    | NASDAQ   | rr15.low    | 2026-09-24 | 760.42 |
      | SPY    | NASDAQ   | rr15.low    | 2026-09-23 | 755.10 |
    When I list features for "SPY"
    Then the command succeeds
    And the feature list reads back as:
      | line                                   |
      | SPY \| 2026-09-24 \| rr15.high \| 780.72 |
      | SPY \| 2026-09-23 \| rr15.low \| 755.1  |
      | SPY \| 2026-09-24 \| rr15.low \| 760.42  |

  Scenario: Delete removes all dates
    Given stored features:
      | symbol | exchange | feature  | date       | value  |
      | SPY    | NASDAQ   | rr15.low | 2026-09-23 | 755.10 |
      | SPY    | NASDAQ   | rr15.low | 2026-09-24 | 760.42 |
    When I delete feature "rr15.low" for "SPY"
    Then the command succeeds
    And 2 rows were removed
    And showing feature "rr15.low" for "SPY" reports not found
