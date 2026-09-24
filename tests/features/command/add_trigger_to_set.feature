Feature: Add trigger to set command
  As a MrMkt operator
  I want to add stored triggers to a trigger set
  So that add behaves deterministically

  Scenario: Set add stores the membership
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    When I add trigger "dip-watch" to set "my-set"
    Then the command succeeds
    And set "my-set" contains "dip-watch"

  Scenario: Set add rejects an unknown set
    When the trigger "dip-watch" is added to triggerset "no-such-set"
    Then the command fails with errors:
      | field      | message                            |
      | triggerset | Triggerset 'no-such-set' not found |

  Scenario: Set add rejects an unknown trigger
    Given trigger set "my-set" exists
    When the trigger "no-such-trigger" is added to triggerset "my-set"
    Then the command fails with errors:
      | field   | message                             |
      | trigger | Trigger 'no-such-trigger' not found |

  Scenario: Catch all errors
    When the trigger "trigger-missing" is added to triggerset "trigerset-missing"
    Then the command fails with errors:
      | field      | message                             |
      | trigger    | Trigger 'trigger-missing' not found |
      | triggerset | Triggerset 'trigerset-missing' not found |
