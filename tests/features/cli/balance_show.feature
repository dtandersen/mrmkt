Feature: Balance show CLI
  As a MrMkt operator
  I want to show the paper-account balance from the CLI
  So that equity output is exact on the console

  Scenario: Show the account balance
    Given the paper account balance is:
      | equity   | cash     | buying_power | portfolio_value | currency |
      | 100000.0 | 60000.0  | 120000.0     | 100000.0        | USD      |
    When I execute "mrmkt balance show"
    Then the command succeeds
    And the console displays:
      """
      equity,cash,buying_power,portfolio_value,currency
      100000.0,60000.0,120000.0,100000.0,USD
      """

  Scenario: Report a balance read failure
    Given the paper balance request fails
    When I execute "mrmkt balance show"
    Then the command fails
    And the output reports "Failed to show balance: paper trading unavailable"
