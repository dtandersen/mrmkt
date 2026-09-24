Feature: Trigger delete CLI
  As a MrMkt operator
  I want to delete a stored trigger from the CLI
  So that delete output and errors are exact on the console

  Scenario: Delete rejects an unknown name
    When I execute "mrmkt trigger delete no-such-trigger"
    Then the command fails
    And the console displays:
      """
      Usage: root trigger delete [OPTIONS] {name}
      Try 'root trigger delete --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: no trigger with name 'no-such-trigger'                        │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """

  Scenario: Deleting a trigger cascades out of its sets
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    And trigger "dip-watch" is in set "my-set"
    When I execute "mrmkt trigger delete dip-watch"
    Then the command succeeds
    And the console displays:
      """
      deleted trigger dip-watch
      """
