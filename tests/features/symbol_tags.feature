Feature: Tag local ticker symbols
  As a MrMkt operator
  I want to add and remove labels on ticker symbols
  So that I can select named groups such as the S&P 500

  Scenario: Label a ticker and filter the symbol list by that tag
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    When I execute "mrmkt symbols label AAPL sp500"
    Then the command succeeds
    And ticker "AAPL" on "NASDAQ" has tag "sp500"
    When I execute "mrmkt symbols list --tag sp500"
    Then the symbol list contains:
      | symbol | exchange |
      | AAPL   | NASDAQ   |

  Scenario: Label every local listing for the requested symbol
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | AAPL   | ARCA     | us_equity |
    When I execute "mrmkt symbols label AAPL sp500"
    Then the command succeeds
    And ticker "AAPL" on "NASDAQ" has tag "sp500"
    And ticker "AAPL" on "ARCA" has tag "sp500"
    And the output reports 2 tag assignments

  Scenario: Labeling an already tagged ticker is idempotent
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    When I execute "mrmkt symbols label AAPL sp500"
    Then the command succeeds
    And the output reports 0 new tag assignments

  Scenario: Label a comma-separated group of symbols
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    When I execute "mrmkt symbols label AAPL,MSFT sp500"
    Then the command succeeds
    And ticker "AAPL" on "NASDAQ" has tag "sp500"
    And ticker "MSFT" on "NASDAQ" has tag "sp500"
    And the output reports 2 tag assignments

  Scenario: Remove a tag from a ticker
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    When I execute "mrmkt symbols unlabel AAPL sp500"
    Then the command succeeds
    And ticker "AAPL" on "NASDAQ" has no tags
