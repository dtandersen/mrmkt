Feature: Order create CLI
  As a MrMkt operator
  I want to submit paper limit orders from the CLI
  So that resting buy-the-dip orders are exact on the console

  Scenario: Create a buy limit order with a stop
    When I execute "mrmkt order create BOX --buy 10 --price 31.27 --stop 29.50"
    Then the command succeeds
    And the console displays:
      """
      id,symbol,side,qty,filled_qty,limit_price,stop_price,status,type,time_in_force
      fake-0001,BOX,buy,10.0,0.0,31.27,29.5,new,limit,day
      """
    And the paper account received a limit buy for "BOX" at 31.27 with stop 29.5

  Scenario: Day is the default time in force with a gtc escape hatch
    When I execute "mrmkt order create BOX --buy 10 --price 31.27 --tif gtc"
    Then the command succeeds
    And the console displays:
      """
      id,symbol,side,qty,filled_qty,limit_price,stop_price,status,type,time_in_force
      fake-0001,BOX,buy,10.0,0.0,31.27,,new,limit,gtc
      """

  Scenario: Create rejects a bad time in force
    When I execute "mrmkt order create BOX --buy 10 --price 31.27 --tif week"
    Then the command fails
    And the output reports "time in force must be 'day' or 'gtc'"

  Scenario: Create requires exactly one of buy or sell
    When I execute "mrmkt order create BOX --price 31.27"
    Then the command fails
    And the output reports "provide exactly one of --buy or --sell"

  Scenario: Create rejects a non-positive quantity
    When I execute "mrmkt order create BOX --buy 0 --price 31.27"
    Then the command fails
    And the output reports "quantity must be > 0"

  Scenario: Create rejects a buy stop at or above the limit
    When I execute "mrmkt order create BOX --buy 10 --price 31.27 --stop 32.00"
    Then the command fails
    And the output reports "buy stop must be below the limit price"

  Scenario: Report a submit failure
    Given the paper order request fails
    When I execute "mrmkt order create BOX --buy 10 --price 31.27"
    Then the command fails
    And the output reports "Failed to create order: paper trading unavailable"
