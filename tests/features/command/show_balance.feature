Feature: Show balance command
  As a MrMkt operator
  I want to read the paper-account balance deterministically
  So that balance behavior is exact before touching the paper account

  Scenario: Show returns the account snapshot
    Given the paper account balance is:
      | equity   | cash     | buying_power | portfolio_value | currency |
      | 100000.0 | 60000.0  | 120000.0     | 100000.0        | USD      |
    When I show the paper balance
    Then the command succeeds
    And the shown balance is 100000.0 equity with 60000.0 cash

  Scenario: Show reports a broker failure
    Given the paper balance request fails
    When I show the paper balance
    Then the positions command fails
