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
    When I add trigger "dip-watch" to set "no-such-set"
    Then the command fails with errors:
      | field | message                             |
      | set   | no trigger set with name 'no-such-set' |

  Scenario: Set add rejects an unknown trigger
    Given trigger set "my-set" exists
    When I add trigger "no-such-trigger" to set "my-set"
    Then the command fails with errors:
      | field   | message                                |
      | trigger | no trigger with name 'no-such-trigger' |
