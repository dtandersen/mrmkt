Feature: Import daily prices from Alpaca
  As a MrMkt operator
  I want to import adjusted daily price bars
  So that prices are available in the local database for analysis

  Scenario: Import price bars for selected symbols and date range
    Given Alpaca returns these daily bars:
      | symbol | date       | open | high | low  | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99   | 104   | 1000   |
      | AAPL   | 2024-01-03 | 104  | 107  | 103  | 106   | 1200   |
      | MSFT   | 2024-01-02 | 300  | 305  | 299  | 304   | 800    |
    When I execute "mrmkt prices import --provider alpaca AAPL MSFT --from 2024-01-01 --to 2024-01-31"
    Then the command succeeds
    And Alpaca receives the symbols "AAPL,MSFT"
    And Alpaca receives the date range from "2024-01-01" to "2024-01-31"
    And the local price catalog contains these daily bars:
      | symbol | date       | open | high | low  | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99   | 104   | 1000   |
      | AAPL   | 2024-01-03 | 104  | 107  | 103  | 106   | 1200   |
      | MSFT   | 2024-01-02 | 300  | 305  | 299  | 304   | 800    |
    And the import reports 3 new daily bars

  Scenario: Import all locally cataloged symbols when explicitly requested
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    And Alpaca returns these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
      | MSFT   | 2024-01-02 | 300  | 305  | 299 | 304   | 800    |
    When I execute "mrmkt prices import --provider alpaca --all --from 2024-01-01 --to 2024-01-31"
    Then the command succeeds
    And Alpaca receives the symbols "AAPL,MSFT"
    And the import reports 2 new daily bars

  Scenario: Import symbols selected by tag
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
      | NVDA   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    And ticker "MSFT" on "NASDAQ" already has tag "sp500"
    And Alpaca returns these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
      | MSFT   | 2024-01-02 | 300  | 305  | 299 | 304   | 800    |
      | NVDA   | 2024-01-02 | 500  | 510  | 490 | 505   | 700    |
    When I execute "mrmkt prices import --provider alpaca --tag sp500 --from 2024-01-01 --to 2024-01-31"
    Then the command succeeds
    And Alpaca receives the symbols "AAPL,MSFT"
    And the import reports 2 new daily bars

  Scenario: Re-importing existing bars does not create duplicates
    Given the local price catalog already contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
    And Alpaca returns these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
    When I execute "mrmkt prices import --provider alpaca AAPL --from 2024-01-01 --to 2024-01-31"
    Then the command succeeds
    And the local price catalog contains exactly one "AAPL" bar on "2024-01-02"
    And the import reports 0 new daily bars

  Scenario: Reject an inverted date range before requesting Alpaca data
    When I execute "mrmkt prices import --provider alpaca AAPL --from 2024-02-01 --to 2024-01-01"
    Then the command fails
    And no Alpaca request is sent
    And the local price catalog remains empty

  Scenario: Report an Alpaca market-data failure without writing prices
    Given the Alpaca price request fails
    When I execute "mrmkt prices import --provider alpaca AAPL --from 2024-01-01 --to 2024-01-31"
    Then the command fails
    And the local price catalog remains empty

  Scenario: Use the fake clock as the end of a relative date range
    Given the fake clock says today is "2026-06-28"
    And Alpaca returns these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2026-01-02 | 100  | 105  | 99  | 104   | 1000   |
    When I execute "mrmkt prices import --provider alpaca AAPL --from 180d"
    Then the command succeeds
    And Alpaca receives the symbols "AAPL"
    And Alpaca receives the date range from "2025-12-30" to "2026-06-28"
    And the import reports 1 new daily bar
