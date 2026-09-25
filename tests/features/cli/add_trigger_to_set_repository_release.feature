Feature: Triggerset add releases the repository
  As a MrMkt operator
  I want the triggerset add CLI to release the repository it was handed
  So that no database connection leaks whether the add succeeds or fails

  Scenario: Successful add releases the repository
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    When I execute "mrmkt triggerset add my-set dip-watch"
    Then the command succeeds
    And the repository is released

  Scenario: Failed add releases the repository
    Given trigger "dip-watch" exists
    When I execute "mrmkt triggerset add no-such-set dip-watch"
    Then the command fails
    And the repository is released
