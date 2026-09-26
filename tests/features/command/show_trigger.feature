Feature: Trigger show command
  As a MrMkt operator
  I want to show a stored trigger by name
  So that show behaves deterministically

  Scenario: Show returns the stored trigger
    Given trigger "dip-watch" exists
    When I show trigger "dip-watch"
    Then the command succeeds
    And the trigger "dip-watch" has:
      | field     | value          |
      | symbol    | AAA            |
      | indicator    | risk-range     |
      | operator  | crossing-down  |
      | value     |                |
      | frequency | once_per_rearm |
      | expires   |                |
      | message   |                |
      | enabled   | true           |

  Scenario: Show rejects an unknown name
    When I show trigger "no-such-trigger"
    Then the command fails with errors:
      | field | message                                |
      | name  | no trigger with name 'no-such-trigger' |
