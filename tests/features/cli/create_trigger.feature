Feature: Create a trigger
  As a MrMkt operator
  I want to store named realtime triggers
  So that watch can monitor a saved trigger set

  Scenario: Create names the trigger explicitly
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    And the output mentions "id,name,symbol,signal,operator,value,frequency,expires_at,message,enabled"
    And the output mentions "dip-watch"
    And the output mentions "AAA"

  Scenario: Create without a name defaults to trigger-######
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create --symbol AAA --operator crossing-down"
    Then the command succeeds
    And the output mentions "trigger-"

  Scenario: Create requires a symbol
    When I execute "mrmkt trigger create dip-watch --operator crossing-down"
    Then the command fails
    And the output mentions "--symbol"

  Scenario: Create rejects an unknown operator
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator sideways"
    Then the command fails
    And the output mentions "unknown operator"

  Scenario: Create rejects a duplicate name
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-up"
    Then the command fails
    And the output mentions "already exists"

  Scenario: Create rejects a bad frequency
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --frequency sometimes"
    Then the command fails
    And the output mentions "unknown frequency"

  Scenario: Create rejects a duplicate symbol and operator
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create first --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt trigger create second --symbol AAA --operator crossing-down"
    Then the command fails
    And the output mentions "already exists"

  Scenario: List, disable, enable, and remove round trip
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt trigger list"
    Then the command succeeds
    And the output mentions "dip-watch"
    When I execute "mrmkt trigger disable 1"
    Then the command succeeds
    And the output mentions "disabled"
    When I execute "mrmkt trigger enable 1"
    Then the command succeeds
    And the output mentions "enabled"
    When I execute "mrmkt trigger remove 1"
    Then the command succeeds
    And the output mentions "removed trigger 1"
