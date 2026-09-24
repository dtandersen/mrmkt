Feature: Trigger commands
  As a MrMkt operator
  I want to store named realtime triggers and trigger sets
  So that watch can monitor a saved trigger set

  Scenario: Create names the trigger explicitly
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    And the output mentions "name,symbol,signal,operator,value,frequency,expires_at,message,enabled"
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
    And the output mentions "'sideways' is an invalid operator"

  Scenario: Create rejects a duplicate symbol and operator
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create first --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt trigger create second --symbol AAA --operator crossing-down"
    Then the command fails
    And the output mentions "already exists"

  Scenario: Show, list, and delete round trip by name
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt trigger show dip-watch"
    Then the command succeeds
    And the output mentions "dip-watch"
    And the output mentions "AAA"
    When I execute "mrmkt trigger list"
    Then the command succeeds
    And the output mentions "dip-watch"
    When I execute "mrmkt trigger delete dip-watch"
    Then the command succeeds
    And the output mentions "deleted trigger dip-watch"
    When I execute "mrmkt trigger list"
    Then the command succeeds

  Scenario: Show rejects an unknown name
    When I execute "mrmkt trigger show no-such-trigger"
    Then the command fails
    And the output mentions "no trigger with name 'no-such-trigger'"

  Scenario: Delete rejects an unknown name
    When I execute "mrmkt trigger delete no-such-trigger"
    Then the command fails
    And the output mentions "no trigger with name 'no-such-trigger'"

  Scenario: Trigger sets round trip by name
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt triggerset create my-set"
    Then the command succeeds
    And the output mentions "created trigger set my-set"
    When I execute "mrmkt triggerset add my-set dip-watch"
    Then the command succeeds
    And the output mentions "added trigger dip-watch to trigger set my-set"
    When I execute "mrmkt triggerset remove my-set dip-watch"
    Then the command succeeds
    And the output mentions "removed trigger dip-watch from trigger set my-set"

  Scenario: Triggerset create without a name defaults to triggerset-######
    When I execute "mrmkt triggerset create"
    Then the command succeeds
    And the output mentions "triggerset-"

  Scenario: Triggerset create rejects a duplicate name
    When I execute "mrmkt triggerset create my-set"
    Then the command succeeds
    When I execute "mrmkt triggerset create my-set"
    Then the command fails
    And the output mentions "already exists"

  Scenario: Triggerset add rejects an unknown set
    When I execute "mrmkt triggerset add no-such-set dip-watch"
    Then the command fails
    And the output mentions "no trigger set with name 'no-such-set'"

  Scenario: Triggerset add rejects an unknown trigger
    When I execute "mrmkt triggerset create my-set"
    Then the command succeeds
    When I execute "mrmkt triggerset add my-set no-such-trigger"
    Then the command fails
    And the output mentions "no trigger with name 'no-such-trigger'"

  Scenario: Triggerset remove rejects a non-member
    When I execute "mrmkt triggerset create my-set"
    Then the command succeeds
    When I execute "mrmkt triggerset remove my-set dip-watch"
    Then the command fails
    And the output mentions "no trigger 'dip-watch' in trigger set 'my-set'"

  Scenario: Deleting a trigger cascades out of its sets
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt triggerset create my-set"
    Then the command succeeds
    When I execute "mrmkt triggerset add my-set dip-watch"
    Then the command succeeds
    When I execute "mrmkt trigger delete dip-watch"
    Then the command succeeds
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    When I execute "mrmkt triggerset remove my-set dip-watch"
    Then the command fails
    And the output mentions "no trigger 'dip-watch' in trigger set 'my-set'"
