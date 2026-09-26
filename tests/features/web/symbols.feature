Feature: Symbol web fragment
  As a MrMkt operator
  I want to browse the local ticker catalog in a browser
  So that stored symbols are visible without the CLI

  Scenario: Fragment lists stored symbols in a stable order
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | MSFT   | NASDAQ   | us_equity |
      | AAPL   | NASDAQ   | us_equity |
    When I open "/fragments/symbols"
    Then the web command succeeds
    And the symbol fragment lists these rows in order:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |

  Scenario: Fragment reports an empty ticker catalog
    Given the local ticker catalog is empty
    When I open "/fragments/symbols"
    Then the web command succeeds
    And the fragment says no symbols were found

  Scenario: Fragment filters by tag
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    When I open "/fragments/symbols?tag=sp500"
    Then the web command succeeds
    And the symbol fragment lists these rows in order:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |

  Scenario: Fragment rejects an invalid tag
    When I open "/fragments/symbols?tag=bad%20tag"
    Then the web command fails with status 400
    And the fragment reports an error
