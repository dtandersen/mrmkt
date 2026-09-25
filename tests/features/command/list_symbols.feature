Feature: List stored symbols command
  As a MrMkt operator
  I want to list stored symbols deterministically
  So that listing behaves the same regardless of insertion order

  Scenario: List returns stored symbols in a stable order
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | MSFT   | NASDAQ   | us_equity |
      | AAPL   | NASDAQ   | us_equity |
    When I list stored symbols
    Then the command succeeds
    And the stored symbols are:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |

  Scenario: List of an empty catalog returns no symbols
    Given the local ticker catalog is empty
    When I list stored symbols
    Then the command succeeds
    And no stored symbols are listed

  Scenario: List filtered by tag returns only tagged symbols
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    When I list stored symbols tagged "sp500"
    Then the command succeeds
    And the stored symbols are:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |

  Scenario: List filtered by an unused tag returns no symbols
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    When I list stored symbols tagged "sp500"
    Then the command succeeds
    And no stored symbols are listed
