Feature: Price web fragment
  As a MrMkt operator
  I want to browse stored daily bars in a browser
  So that price history is visible without the CLI

  Scenario: Fragment lists stored bars
    Given the local price catalog contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
    When I open "/fragments/prices?symbols=AAPL"
    Then the web command succeeds
    And the price fragment lists these rows in order:
      | symbol | date       | close |
      | AAPL   | 2024-01-02 | 104   |

  Scenario: Fragment reports no stored bars
    Given the local ticker catalog is empty
    When I open "/fragments/prices?symbols=AAPL"
    Then the web command succeeds
    And the fragment says no prices were found
