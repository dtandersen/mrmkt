Feature: Trigger set create command
  As a MrMkt operator
  I want to create named trigger sets
  So that set creation behaves deterministically

  Scenario: Set create without a name defaults to triggerset-######
    Given the next trigger name is "triggerset-123456"
    When I create a trigger set with no name
    Then the command succeeds
    And the result is "triggerset-123456"

  Scenario: Set create rejects a duplicate name
    When I create trigger set "my-set"
    Then the command succeeds
    When I create trigger set "my-set"
    Then the command fails with errors:
      | field | message                         |
      | set   | trigger set 'my-set' already exists |
