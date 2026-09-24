Feature: List imported stock symbols
  As a MrMkt operator
  I want to inspect the local ticker catalog
  So that I know which symbols are available for analysis

  Scenario: List stored symbols in a stable order
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | MSFT   | NASDAQ   | us_equity |
      | AAPL   | NASDAQ   | us_equity |
    When I run "mrmkt symbols list"
    Then the command succeeds
    And the symbol table lists these rows in order:
      | symbol | exchange | type      |
      | AAPL   | NASDAQ   | us_equity |
      | MSFT   | NASDAQ   | us_equity |

  Scenario: Report an empty ticker catalog
    Given the local ticker catalog is empty
    When I run "mrmkt symbols list"
    Then the command succeeds
    And the output says no symbols were found

  Scenario: Report a local catalog read failure
    Given the local ticker catalog cannot be read
    When I run "mrmkt symbols list"
    Then the command fails
    And the output reports that listing symbols failed
