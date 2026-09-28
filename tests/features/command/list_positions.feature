Feature: List positions command
  As a MrMkt operator
  I want to list paper-account positions deterministically
  So that positions behave the same regardless of broker order

  Scenario: List returns positions in symbol order
    Given the paper account holds these positions:
      | symbol | qty | avg_entry_price | current_price | market_value | unrealized_pl |
      | MSFT   | 10  | 400.0           | 420.0         | 4200.0       | 200.0         |
      | AAPL   | 5   | 200.0           | 210.0         | 1050.0       | 50.0          |
    When I list paper positions
    Then the command succeeds
    And the stored positions are:
      | symbol | qty  | avg_entry_price |
      | AAPL   | 5.0  | 200.0           |
      | MSFT   | 10.0 | 400.0           |

  Scenario: List of an empty account returns no positions
    Given the paper account holds no positions
    When I list paper positions
    Then the command succeeds
    And no paper positions are listed

  Scenario: List reports a broker failure
    Given the paper positions request fails
    When I list paper positions
    Then the positions command fails
