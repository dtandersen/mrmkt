Feature: Remove trigger from set command
  As a MrMkt operator
  I want to remove stored triggers from a trigger set
  So that remove behaves deterministically

  Scenario: Set remove drops the membership
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    And trigger "dip-watch" is in set "my-set"
    When I remove trigger "dip-watch" from set "my-set"
    Then the command succeeds
    And set "my-set" is empty

  Scenario: Set remove rejects a non-member
    Given trigger set "my-set" exists
    When I remove trigger "dip-watch" from set "my-set"
    Then the command fails with errors:
      | field   | message                                          |
      | trigger | no trigger 'dip-watch' in trigger set 'my-set' |
