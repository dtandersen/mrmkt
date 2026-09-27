Feature: Watch CLI argument forwarding
  As a MrMkt operator
  I want mrmkt watch to pass its arguments to the watch command
  So that the requested symbols are subscribed to

  Background:
    Given the daily price history of AAA from 2022-01-03 to 2022-02-14 rising 0.2 per day

  Scenario: Watch forwards explicit symbols
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | BBB    | NASDAQ   | us_equity |
    And the daily price history of BBB from 2022-01-03 to 2022-01-07 rising 1.0 per day
    When I execute "mrmkt watch AAA BBB"
    Then the command succeeds
    And the output is:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      """

  Scenario: Watch forwards a stored trigger selection
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    When I execute "mrmkt watch --trigger 1"
    Then the command succeeds
    And the output is:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      """
