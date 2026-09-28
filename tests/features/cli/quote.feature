Feature: Quote CLI
  As a MrMkt operator
  I want the current price of a stock from the CLI
  So that quote output is exact on the console

  Scenario: Quote one symbol
    Given the data feed quotes:
      | symbol | bid   | ask   | timestamp                 |
      | BOX    | 31.40 | 31.42 | 2026-09-26T15:59:00+00:00 |
    When I execute "mrmkt quote BOX"
    Then the command succeeds
    And the console displays:
      """
      symbol,bid,ask,timestamp
      BOX,31.4,31.42,2026-09-26T15:59:00+00:00
      """

  Scenario: Quote rejects an invalid symbol
    When I execute "mrmkt quote '!!!'"
    Then the command fails
    And the output reports "invalid stock symbol"

  Scenario: Quote reports an unknown symbol
    Given the data feed quotes:
      | symbol | bid   | ask   | timestamp                 |
      | BOX    | 31.40 | 31.42 | 2026-09-26T15:59:00+00:00 |
    When I execute "mrmkt quote NOPE"
    Then the command fails
    And the output reports "no quote for symbol 'NOPE'"

  Scenario: Report a quote request failure
    Given the data feed request fails
    When I execute "mrmkt quote BOX"
    Then the command fails
    And the output reports "Failed to get quote: paper data unavailable"
