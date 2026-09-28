Feature: Get quote command
  As a MrMkt operator
  I want the latest quote for one symbol deterministically
  So that quote behavior is exact before touching the live feed

  Scenario: Get returns the latest quote
    Given the data feed quotes:
      | symbol | bid   | ask   | timestamp                 |
      | BOX    | 31.40 | 31.42 | 2026-09-26T15:59:00+00:00 |
    When I get the quote for "BOX"
    Then the command succeeds
    And the quoted price is bid 31.4 ask 31.42 for "BOX"

  Scenario: Get rejects an invalid symbol
    When I get the quote for "!!!"
    Then the quote command fails

  Scenario: Get reports an unknown symbol
    Given the data feed has no quotes
    When I get the quote for "NOPE"
    Then the quote command fails

  Scenario: Get reports a feed failure
    Given the data feed request fails
    When I get the quote for "BOX"
    Then the quote command fails
