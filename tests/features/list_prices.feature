Feature: List locally stored prices
  As a MrMkt operator
  I want to list stored daily prices for selected symbols
  So that I can inspect the imported price history

  Scenario: List prices for selected symbols within a date range
    Given the local price catalog contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2023-12-29 | 190  | 192  | 189 | 191   | 900    |
      | MSFT   | 2024-01-02 | 300  | 305  | 299 | 304   | 800    |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
    When I execute "mrmkt prices list AAPL MSFT --from 2024-01-01 --to 2024-01-31"
    Then the command succeeds
    And the price table lists these rows in order:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2024-01-02 | 100  | 105  | 99  | 104   | 1000   |
      | MSFT   | 2024-01-02 | 300  | 305  | 299 | 304   | 800    |

  Scenario: Report when no prices match the requested range
    Given the local price catalog contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | AAPL   | 2023-12-29 | 190  | 192  | 189 | 191   | 900    |
    When I execute "mrmkt prices list AAPL --from 2024-01-01 --to 2024-01-31"
    Then the command succeeds
    And the output says no prices were found

  Scenario: Reject an inverted date range
    When I execute "mrmkt prices list AAPL --from 2024-02-01 --to 2024-01-01"
    Then the command fails
