Feature: Triggerset add CLI
  As a MrMkt operator
  I want to add triggers to a trigger set from the CLI
  So that add output and errors are exact on the console

  Scenario: Triggerset add stores the membership
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    When I execute "mrmkt triggerset add my-set dip-watch"
    Then the command succeeds
    And the console displays:
      """
      added trigger dip-watch to trigger set my-set
      """

  Scenario: Triggerset add rejects an unknown set
    When I execute "mrmkt triggerset add no-such-set dip-watch"
    Then the command fails
    And the console displays:
      """
      Triggerset 'no-such-set' not found
      """

  Scenario: Triggerset add rejects an unknown trigger
    Given trigger set "my-set" exists
    When I execute "mrmkt triggerset add my-set no-such-trigger"
    Then the command fails
    And the console displays:
      """
      Usage: root triggerset add [OPTIONS] {set_name} {trigger_name}
      Try 'root triggerset add --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: no trigger with name 'no-such-trigger'                        │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """
