Feature: Watch CLI argument forwarding
  As a MrMkt operator
  I want mrmkt watch to pass its arguments to the watch command
  So that the requested symbols are subscribed to

  Scenario: Watch forwards explicit symbols
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | BBB    | NASDAQ   | us_equity |
    And AAA has a 60-bar climb with a dip
    And BBB has a 5-bar climb
    When I execute "mrmkt watch AAA BBB"
    Then the command succeeds
    And the price source receives symbols "AAA"
    And the output is:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-03-25.
      """

  Scenario: Watch forwards a stored trigger selection
    Given AAA has a 60-bar climb with a dip
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    When I execute "mrmkt watch --trigger 1"
    Then the command succeeds
    And the price source receives symbols "AAA"
