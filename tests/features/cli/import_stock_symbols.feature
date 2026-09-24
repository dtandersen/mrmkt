Feature: Import stock symbols from Alpaca
  As a MrMkt operator
  I want to import Alpaca's active, tradable US-equity assets
  So that they are available in the local ticker catalog

  Scenario: Import active, tradable US-equity symbols
    Given Alpaca returns these assets:
      | symbol | exchange | asset_class | status | tradable |
      | AAPL   | NASDAQ   | us_equity   | active | true     |
      | MSFT   | NASDAQ   | us_equity   | active | true     |
    And the local ticker catalog is empty
    When I run "mrmkt symbols import --provider alpaca"
    Then the command succeeds
    And the local ticker catalog contains:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    And the import reports 2 newly imported symbols

  Scenario: Exclude inactive, non-tradable, and non-equity assets
    Given Alpaca returns these assets:
      | symbol  | exchange | asset_class | status   | tradable |
      | AAPL    | NASDAQ   | us_equity   | active   | true     |
      | OLD     | NYSE     | us_equity   | inactive | true     |
      | LOCKED  | NYSE     | us_equity   | active   | false    |
      | BTC/USD |          | crypto      | active   | true     |
    And the local ticker catalog is empty
    When I run "mrmkt symbols import --provider alpaca"
    Then the command succeeds
    And the local ticker catalog contains:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    And the import reports 1 newly imported symbol

  Scenario: Re-importing symbols does not create duplicates
    Given the local ticker catalog already contains:
      | symbol | exchange |
      | MSFT   | NASDAQ   |
    And Alpaca returns these assets:
      | symbol | exchange | asset_class | status | tradable |
      | MSFT   | NASDAQ   | us_equity   | active | true     |
      | AAPL   | NASDAQ   | us_equity   | active | true     |
    When I run "mrmkt symbols import --provider alpaca"
    Then the command succeeds
    And the local ticker catalog contains exactly one "MSFT" on "NASDAQ"
    And the local ticker catalog contains exactly one "AAPL" on "NASDAQ"
    And the import reports 1 newly imported symbol

  Scenario: Empty Alpaca asset catalog
    Given Alpaca returns no assets
    And the local ticker catalog is empty
    When I run "mrmkt symbols import --provider alpaca"
    Then the command succeeds
    And the local ticker catalog remains empty
    And the import reports 0 newly imported symbols

  Scenario: Alpaca request fails
    Given the Alpaca asset request fails
    And the local ticker catalog is empty
    When I run "mrmkt symbols import --provider alpaca"
    Then no symbols are added to the local ticker catalog
    And the import reports a failure
