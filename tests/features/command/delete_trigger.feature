Feature: Trigger delete command
  As a MrMkt operator
  I want to delete a stored trigger by name
  So that delete behaves deterministically

  Scenario: Delete removes the stored trigger
    Given trigger "dip-watch" exists
    When I delete trigger "dip-watch"
    Then the command succeeds
    And trigger "dip-watch" is gone

  Scenario: Delete rejects an unknown name
    When I delete trigger "no-such-trigger"
    Then the command fails with errors:
      | field | message                                |
      | name  | no trigger with name 'no-such-trigger' |

  Scenario: Deleting a trigger cascades out of its sets
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    And trigger "dip-watch" is in set "my-set"
    When I delete trigger "dip-watch"
    Then the command succeeds
    And set "my-set" is empty
