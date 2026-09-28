Feature: Position list CLI
  As a MrMkt operator
  I want to list paper-account positions from the CLI
  So that position output is exact on the console

  Scenario: List open positions in symbol order
    Given the paper account holds these positions:
      | symbol | qty | avg_entry_price | current_price | market_value | unrealized_pl |
      | MSFT   | 10  | 400.0           | 420.0         | 4200.0       | 200.0         |
      | AAPL   | 5   | 200.0           | 210.0         | 1050.0       | 50.0          |
    When I execute "mrmkt position list"
    Then the command succeeds
    And the console displays:
      """
      symbol,qty,avg_entry,current,market_value,unrealized_pl
      AAPL,5.0,200.0,210.0,1050.0,50.0
      MSFT,10.0,400.0,420.0,4200.0,200.0
      """

  Scenario: Report an empty paper account
    Given the paper account holds no positions
    When I execute "mrmkt position list"
    Then the command succeeds
    And the console displays:
      """
      symbol,qty,avg_entry,current,market_value,unrealized_pl
      """

  Scenario: Report a positions read failure
    Given the paper positions request fails
    When I execute "mrmkt position list"
    Then the command fails
    And the output reports "Failed to list positions: paper trading unavailable"
