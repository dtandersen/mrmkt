Feature: Triggerset remove CLI
  As a MrMkt operator
  I want to remove triggers from a trigger set from the CLI
  So that remove output and errors are exact on the console

  Scenario: Triggerset remove drops the membership
    Given trigger "dip-watch" exists
    And trigger set "my-set" exists
    And trigger "dip-watch" is in set "my-set"
    When I execute "mrmkt triggerset remove my-set dip-watch"
    Then the command succeeds
    And the console displays:
      """
      removed trigger dip-watch from trigger set my-set
      """

  Scenario: Triggerset remove rejects a non-member
    Given trigger set "my-set" exists
    When I execute "mrmkt triggerset remove my-set dip-watch"
    Then the command fails
    And the console displays:
      """
      Usage: root triggerset remove [OPTIONS] {set_name} {trigger_name}
      Try 'root triggerset remove --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: no trigger 'dip-watch' in trigger set 'my-set'                │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """
