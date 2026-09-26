Feature: Trigger create command
  As a MrMkt operator
  I want to store named realtime triggers
  So that create validation behaves deterministically

  Scenario: Create stores every field
    When I create a trigger with:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
      | value     | 95.5          |
      | frequency | once          |
      | expires   | 2026-12-31    |
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value         |
      | symbol    | AAA           |
      | indicator    | risk-range    |
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
      | indicator | risk-range |
    Then the command succeeds
    And the trigger is named "trigger-123456"

  Scenario: Create reports all invalid fields at once
    When I create a trigger with:
      | field     | value      |
      | name      | dip-watch  |
      | symbol    | !!!        |
      | operator  | sideways   |
      | frequency | sometimes  |
      | indicator    | bad!  |
      | expires   | not-a-date |
    Then the command fails with errors:
      | field     | message                                                      |
      | operator  | 'sideways' is an invalid operator                            |
      | frequency | 'sometimes' is an invalid frequency                          |
      | indicator    | 'bad!' is an invalid indicator (use letters, numbers, '-' or '_') |
      | symbol    | invalid stock symbol: !!!                                    |
      | expires   | --expires must be YYYY-MM-DD                                |

  Scenario: Create rejects a duplicate name
    When I create a trigger with:
      | field    | value         |
      | name     | dip-watch     |
      | symbol   | AAA           |
      | indicator | risk-range   |
      | operator | crossing-down |
    Then the command succeeds
    When I create a trigger with:
      | field    | value       |
      | name     | dip-watch   |
      | symbol   | BBB         |
      | indicator | risk-range |
      | operator | crossing-up |
    Then the command fails with errors:
      | field | message                               |
      | name  | trigger name 'dip-watch' already exists |

  Scenario: Create rejects a duplicate symbol and operator
    When I create a trigger with:
      | field    | value         |
      | name     | first         |
      | symbol   | AAA           |
      | indicator | risk-range   |
      | operator | crossing-down |
    Then the command succeeds
    When I create a trigger with:
      | field    | value         |
      | name     | second        |
      | symbol   | AAA           |
      | indicator | risk-range   |
      | operator | crossing-down |
    Then the command fails with errors:
      | field   | message                                                   |
      | trigger | trigger already exists for AAA risk-range crossing-down |

  Scenario: Create normalizes indicator and symbol
    When I create a trigger with:
      | field  | value      |
      | name   | dip-watch  |
      | symbol | aaa        |
      | indicator | Risk-Range |
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field  | value      |
      | symbol | AAA        |
      | indicator | risk-range |
