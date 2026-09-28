Feature: Manage features from the CLI
  As a MrMkt operator
  I want thin CLI wrappers for the feature commands
  So that scripts can store and read features without SQL

  Scenario: Create, list, show, and delete through the CLI
    Given the ticker catalog contains:
      | symbol | exchange | type      |
      | SPY    | NASDAQ   | us_equity |
    When I execute "mrmkt feature create SPY rr15.low=760.42 --date 2026-09-24"
    Then the command succeeds
    And the output contains "SPY rr15.low=760.42 2026-09-24"
    When I execute "mrmkt feature list SPY"
    Then the command succeeds
    And the output contains "rr15.low"
    When I execute "mrmkt feature show SPY rr15.low"
    Then the command succeeds
    And the output contains "760.42"
    When I execute "mrmkt feature delete SPY rr15.low"
    Then the command succeeds
    And the output contains "Deleted 1 row"

  Scenario: Text feature defaults to the injected current date
    Given the ticker catalog contains:
      | symbol | exchange | type      |
      | SPY    | NASDAQ   | us_equity |
    When I execute "mrmkt feature create SPY trend.state=up"
    Then the command succeeds
    And the output contains "2026-09-27"
    When I execute "mrmkt feature show SPY trend.state"
    Then the command succeeds
    And the output contains "up"

  Scenario: Reject malformed assignments at the CLI boundary
    When I execute "mrmkt feature create SPY trend.state"
    Then the command fails

  Scenario: Show reports a missing feature
    When I execute "mrmkt feature show SPY nope"
    Then the command fails
