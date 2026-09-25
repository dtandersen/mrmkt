Feature: Label and unlabel symbols command
  As a MrMkt operator
  I want to add and remove labels on stored symbols
  So that tagging reports what changed and rejects bad input

  Scenario: Label reports what changed
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    When I label "AAPL" with "sp500"
    Then the command succeeds
    And the tag change is:
      | field   | value |
      | changed | 1     |
      | matched | 1     |
      | tag     | sp500 |
    And ticker "AAPL" on "NASDAQ" has tag "sp500"

  Scenario: Labeling normalizes the symbol and tag
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    When I label "aapl" with "SP500"
    Then the command succeeds
    And ticker "AAPL" on "NASDAQ" has tag "sp500"

  Scenario: Relabeling an already tagged ticker is idempotent
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    When I label "AAPL" with "sp500"
    Then the command succeeds
    And the tag change is:
      | field   | value |
      | changed | 0     |
      | matched | 1     |

  Scenario: Labeling a group applies to every match and counts the rest
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |
    When I label "AAPL,MSFT,ZZZZ" with "sp500"
    Then the command succeeds
    And the tag change is:
      | field     | value |
      | changed   | 2     |
      | matched   | 2     |
      | unmatched | 1     |
    And ticker "AAPL" on "NASDAQ" has tag "sp500"
    And ticker "MSFT" on "NASDAQ" has tag "sp500"

  Scenario: Labeling only unknown symbols fails
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    When I label "ZZZZ" with "sp500"
    Then the command fails with errors:
      | field   | message                                                  |
      | symbols | none of the supplied symbols are in the local ticker catalog |

  Scenario: Labeling with no symbols fails
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    When I label nothing with "sp500"
    Then the command fails with errors:
      | field  | message                                 |
      | symbol | provide at least one comma-separated symbol |

  Scenario: Unlabel removes the tag and reports what changed
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
    And ticker "AAPL" on "NASDAQ" already has tag "sp500"
    When I remove tag "sp500" from "AAPL"
    Then the command succeeds
    And the tag change is:
      | field   | value |
      | changed | 1     |
      | matched | 1     |
    And ticker "AAPL" on "NASDAQ" has no tags
