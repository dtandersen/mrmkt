Feature: Order list CLI
  As a MrMkt operator
  I want to list paper-account orders from the CLI
  So that open-order output is exact on the console

  Scenario: List open orders in symbol order
    Given the paper account has these orders:
      | id      | symbol | side | qty | order_type | status | limit_price | stop_price | filled_qty | time_in_force |
      | order-2 | MSFT   | buy  | 5   | limit      | new    | 400.0       |            | 0          | gtc           |
      | order-1 | AAPL   | buy  | 10  | limit      | new    | 200.0       | 190.0      | 0          | gtc           |
    When I execute "mrmkt order list"
    Then the command succeeds
    And the console displays:
      """
      id,symbol,side,qty,filled_qty,limit_price,stop_price,status,type,time_in_force
      order-1,AAPL,buy,10.0,0.0,200.0,190.0,new,limit,gtc
      order-2,MSFT,buy,5.0,0.0,400.0,,new,limit,gtc
      """

  Scenario: Report no open orders
    Given the paper account has no orders
    When I execute "mrmkt order list"
    Then the command succeeds
    And the console displays:
      """
      id,symbol,side,qty,filled_qty,limit_price,stop_price,status,type,time_in_force
      """

  Scenario: List rejects an unknown status
    When I execute "mrmkt order list --status bogus"
    Then the command fails
    And the output reports "status must be one of: open, closed, all"

  Scenario: Report an order list failure
    Given the paper order request fails
    When I execute "mrmkt order list"
    Then the command fails
    And the output reports "Failed to list orders: paper trading unavailable"
