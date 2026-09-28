Feature: Order show and cancel CLI
  As a MrMkt operator
  I want to inspect and cancel paper-account orders from the CLI
  So that show and cancel output is exact on the console

  Scenario: Show, then cancel, an open order
    Given the paper account has these orders:
      | id      | symbol | side | qty | order_type | status | limit_price | stop_price | filled_qty | time_in_force |
      | order-1 | BOX    | buy  | 10  | limit      | new    | 31.27       | 29.5       | 0          | gtc           |
    When I execute "mrmkt order show order-1"
    Then the command succeeds
    And the console displays:
      """
      id,symbol,side,qty,filled_qty,limit_price,stop_price,status,type,time_in_force
      order-1,BOX,buy,10.0,0.0,31.27,29.5,new,limit,gtc
      """
    When I execute "mrmkt order cancel order-1"
    Then the command succeeds
    And the console displays:
      """
      canceled order order-1
      """
    And the paper account canceled order "order-1"

  Scenario: Show reports an unknown order
    Given the paper account has no orders
    When I execute "mrmkt order show no-such-order"
    Then the command fails
    And the output reports "no order with id 'no-such-order'"

  Scenario: Cancel reports an unknown order
    Given the paper account has no orders
    When I execute "mrmkt order cancel no-such-order"
    Then the command fails
    And the output reports "no order with id 'no-such-order'"
