Feature: Price and ticker import use cases
  As a MrMkt operator
  I want bounded imports with explicit failure accounting
  So that one bad batch never discards thousands of good bars

  Scenario: Imported bars land in the store with duplicates skipped
    Given a clean price store
    And a fake price source serving 5 bars for "AAA"
    When I import "AAA" for the 5-bar window
    Then 5 bars are stored for "AAA"
    When I import "AAA" for the 5-bar window again
    Then 5 bars are stored for "AAA"

  Scenario: A failing batch is recorded, not fatal
    Given a clean price store
    And a fake price source failing batch "AAA,BBB"
    When I import "AAA,BBB" for the 5-bar window
    Then the batch "AAA,BBB" is recorded failed
    And 0 bars are stored for "AAA"

  Scenario: A reversed window is rejected
    Given a clean price store
    And a fake price source serving 5 bars for "AAA"
    When I import "AAA" for a reversed window
    Then the import fails naming the date order

  Scenario: Fetch tickers imports once and skips duplicates
    Given a clean ticker store
    And a fake ticker source serving "AAA" and "BBB"
    When I fetch tickers
    Then 2 tickers are imported
    When I fetch tickers again
    Then 0 tickers are imported
