Feature: Import symbols command
  As a MrMkt operator
  I want to import the remote symbol catalog into the local store
  So that imports are idempotent and reject unsupported providers

  Scenario: Import stores the remote catalog and reports the count
    Given the remote symbol catalog contains:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    And the local ticker catalog is empty
    When I import symbols from "alpaca"
    Then the command succeeds
    And the import count is 2
    And the local ticker catalog contains:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |

  Scenario: Re-importing skips duplicates and reports only new symbols
    Given the local ticker catalog already contains:
      | symbol | exchange |
      | MSFT   | NASDAQ   |
    And the remote symbol catalog contains:
      | symbol | exchange | type      |
      | MSFT   | NASDAQ   | us_equity |
      | AAPL   | NASDAQ   | us_equity |
    When I import symbols from "alpaca"
    Then the command succeeds
    And the import count is 1
    And the local ticker catalog contains exactly one "MSFT" on "NASDAQ"

  Scenario: Import rejects an unsupported provider
    When I import symbols from "tiingo"
    Then the command fails with errors:
      | field    | message                                         |
      | provider | only the 'alpaca' provider is currently supported |
