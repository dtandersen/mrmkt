Feature: Trigger list command
  As a MrMkt operator
  I want to list stored triggers
  So that list behaves deterministically

  Scenario: List returns stored triggers
    Given trigger "dip-watch" exists
    When I list triggers
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value          |
      | symbol    | AAA            |
      | signal    | risk-range     |
      | operator  | crossing-down  |
      | value     |                |
      | frequency | once_per_rearm |
      | expires   |                |
      | message   |                |
      | enabled   | true           |

  Scenario: Enabled-only list hides disabled triggers
    Given trigger "dip-watch" exists
    And trigger "dip-watch" is disabled in the store
    When I list enabled triggers
    Then the command succeeds
    And trigger "dip-watch" is not listed
    When I list triggers
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value          |
      | symbol    | AAA            |
      | signal    | risk-range     |
      | operator  | crossing-down  |
      | value     |                |
      | frequency | once_per_rearm |
      | expires   |                |
      | message   |                |
      | enabled   | false          |
