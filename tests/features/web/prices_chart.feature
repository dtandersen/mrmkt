Feature: Price chart data
  As a MrMkt operator
  I want the landing-page chart to load stored daily bars as JSON
  So that the S&P 500 chart renders without the CLI

  Scenario: Chart data lists stored bars in time order
    Given the local price catalog contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | SPX    | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
      | SPX    | 2024-01-03 | 104  | 108  | 103 | 107   | 1200   |
    When I open "/fragments/prices/chart?symbols=SPX"
    Then the web command succeeds
    And the chart data lists these bars in order:
      | time       | open | high | low | close |
      | 2024-01-02 | 100  | 105  | 99  | 104   |
      | 2024-01-03 | 104  | 108  | 103 | 107   |

  Scenario: Chart data is empty for unknown symbols
    Given the local ticker catalog is empty
    When I open "/fragments/prices/chart?symbols=SPX"
    Then the web command succeeds
    And the chart data is empty

  Scenario: Chart data rejects an invalid symbol
    When I open "/fragments/prices/chart?symbols=bad%20symbol"
    Then the web command fails with status 400
