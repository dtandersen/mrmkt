Feature: Trading order commands
  As a MrMkt operator
  I want to create, list, show, and cancel paper orders
  So that order behavior is exact before touching the paper account

  Scenario: Create submits a limit buy with a stop
    When I create a paper buy of 10 "BOX" at 31.27 stopping at 29.5
    Then the command succeeds
    And the created order is for "BOX" at 31.27 with stop 29.5

  Scenario: Create rejects a non-positive quantity
    When I create a paper buy of 0 "BOX" at 31.27 stopping at nothing
    Then the positions command fails

  Scenario: Create rejects a buy stop at or above the limit
    When I create a paper buy of 10 "BOX" at 31.27 stopping at 32.0
    Then the positions command fails

  Scenario: List returns open orders in symbol order
    Given the paper account has these orders:
      | id      | symbol | side | qty | order_type | status | limit_price | stop_price | filled_qty | time_in_force |
      | order-2 | MSFT   | buy  | 5   | limit      | new    | 400.0       |            | 0          | gtc           |
      | order-1 | AAPL   | buy  | 10  | limit      | new    | 200.0       | 190.0      | 0          | gtc           |
    When I list paper orders
    Then the command succeeds
    And the stored orders are "order-1" then "order-2"

  Scenario: List rejects an unknown status
    When I list paper orders with status "bogus"
    Then the positions command fails

  Scenario: Show returns one order
    Given the paper account has these orders:
      | id      | symbol | side | qty | order_type | status | limit_price | stop_price | filled_qty | time_in_force |
      | order-1 | BOX    | buy  | 10  | limit      | new    | 31.27       | 29.5       | 0          | gtc           |
    When I show paper order "order-1"
    Then the command succeeds
    And the shown order is for "BOX" at 31.27

  Scenario: Show reports an unknown order
    Given the paper account has no orders
    When I show paper order "no-such-order"
    Then the positions command fails

  Scenario: Cancel removes an open order
    Given the paper account has these orders:
      | id      | symbol | side | qty | order_type | status | limit_price | stop_price | filled_qty | time_in_force |
      | order-1 | BOX    | buy  | 10  | limit      | new    | 31.27       | 29.5       | 0          | gtc           |
    When I cancel paper order "order-1"
    Then the command succeeds
    And the paper account canceled order "order-1"

  Scenario: Cancel reports an unknown order
    Given the paper account has no orders
    When I cancel paper order "no-such-order"
    Then the positions command fails
