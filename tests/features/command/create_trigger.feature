Feature: Trigger commands
  As a MrMkt operator
  I want trigger commands to manage stored triggers by name
  So that create, show, list, remove, and trigger sets behave deterministically

  Scenario: Create stores every field
    When I create a trigger with:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | operator  | crossing-down |
      | value     | 95.5          |
      | frequency | once          |
      | expires   | 2026-12-31    |
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value         |
      | symbol    | AAA           |
      | signal    | risk-range    |
      | operator  | crossing-down |
      | value     | 95.5          |
      | frequency | once          |
      | expires   | 2026-12-31    |
      | message   |               |
      | enabled   | true          |

  Scenario: Triggers are automatically named
    Given the next trigger name is "trigger-123456"
    When I create a trigger with:
      | field  | value         |
      | symbol | AAA           |
    Then the command succeeds
    And the trigger is named "trigger-123456"

  Scenario: Create rejects an unknown operator
    When I create a trigger with:
      | field    | value    |
      | name     | dip-watch |
      | symbol   | AAA      |
      | operator | sideways |
    Then the command fails with errors:
      | field    | message                           |
      | operator | 'sideways' is an invalid operator |

  Scenario: Create rejects an unknown frequency
    When I create a trigger with:
      | field     | value     |
      | name      | dip-watch |
      | symbol    | AAA       |
      | frequency | sometimes |
    Then the command fails with errors:
      | field     | message                             |
      | frequency | 'sometimes' is an invalid frequency |

  Scenario: Create rejects a duplicate name
    When I create a trigger with:
      | field    | value         |
      | name     | dip-watch     |
      | symbol   | AAA           |
      | operator | crossing-down |
    Then the command succeeds
    When I create a trigger with:
      | field    | value       |
      | name     | dip-watch   |
      | symbol   | BBB         |
      | operator | crossing-up |
    Then the command fails mentioning "already exists"

  Scenario: Create rejects a duplicate symbol and operator
    When I create a trigger with:
      | field    | value         |
      | name     | first         |
      | symbol   | AAA           |
      | operator | crossing-down |
    Then the command succeeds
    When I create a trigger with:
      | field    | value         |
      | name     | second        |
      | symbol   | AAA           |
      | operator | crossing-down |
    Then the command fails mentioning "already exists"

  Scenario: Show, list, and delete round trip by name
    When I create a trigger with:
      | field    | value         |
      | name     | dip-watch     |
      | symbol   | AAA           |
      | operator | crossing-down |
    Then the command succeeds
    When I show trigger "dip-watch"
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value         |
      | symbol    | AAA           |
      | signal    | risk-range    |
      | operator  | crossing-down |
      | value     |               |
      | frequency | once_per_rearm |
      | expires   |               |
      | message   |               |
      | enabled   | true          |
    When I list triggers
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value         |
      | symbol    | AAA           |
      | signal    | risk-range    |
      | operator  | crossing-down |
      | value     |               |
      | frequency | once_per_rearm |
      | expires   |               |
      | message   |               |
      | enabled   | true          |
    When I delete trigger "dip-watch"
    Then the command succeeds
    When I list triggers
    Then the command succeeds
    And trigger "dip-watch" is not listed

  Scenario: Show rejects an unknown name
    When I show trigger "no-such-trigger"
    Then the command fails mentioning "no trigger with name 'no-such-trigger'"

  Scenario: Delete rejects an unknown name
    When I delete trigger "no-such-trigger"
    Then the command fails mentioning "no trigger with name 'no-such-trigger'"

  Scenario: Enabled-only list hides disabled triggers
    When I create a trigger with:
      | field  | value     |
      | name   | dip-watch |
      | symbol | AAA       |
    Then the command succeeds
    Given trigger "dip-watch" is disabled in the store
    When I list enabled triggers
    Then the command succeeds
    And trigger "dip-watch" is not listed
    When I list triggers
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value         |
      | symbol    | AAA           |
      | signal    | risk-range    |
      | operator  | crossing-down |
      | value     |               |
      | frequency | once_per_rearm |
      | expires   |               |
      | message   |               |
      | enabled   | false         |

  Scenario: Trigger sets round trip by name
    When I create a trigger with:
      | field  | value     |
      | name   | dip-watch |
      | symbol | AAA       |
    Then the command succeeds
    When I create trigger set "my-set"
    Then the command succeeds
    And the result is "my-set"
    When I add trigger "dip-watch" to set "my-set"
    Then the command succeeds
    And set "my-set" contains "dip-watch"
    When I remove trigger "dip-watch" from set "my-set"
    Then the command succeeds
    And set "my-set" is empty

  Scenario: Set create without a name defaults to triggerset-######
    When I create a trigger set with no name
    Then the command succeeds
    And the result starts with "triggerset-"

  Scenario: Set create rejects a duplicate name
    When I create trigger set "my-set"
    Then the command succeeds
    When I create trigger set "my-set"
    Then the command fails mentioning "already exists"

  Scenario: Set add rejects an unknown set
    When I add trigger "dip-watch" to set "no-such-set"
    Then the command fails mentioning "no trigger set with name 'no-such-set'"

  Scenario: Set add rejects an unknown trigger
    When I create trigger set "my-set"
    Then the command succeeds
    When I add trigger "no-such-trigger" to set "my-set"
    Then the command fails mentioning "no trigger with name 'no-such-trigger'"

  Scenario: Set remove rejects a non-member
    When I create trigger set "my-set"
    Then the command succeeds
    When I remove trigger "dip-watch" from set "my-set"
    Then the command fails mentioning "no trigger 'dip-watch' in trigger set 'my-set'"

  Scenario: Deleting a trigger cascades out of its sets
    When I create a trigger with:
      | field  | value     |
      | name   | dip-watch |
      | symbol | AAA       |
    Then the command succeeds
    When I create trigger set "my-set"
    Then the command succeeds
    When I add trigger "dip-watch" to set "my-set"
    Then the command succeeds
    When I delete trigger "dip-watch"
    Then the command succeeds
    And set "my-set" is empty
