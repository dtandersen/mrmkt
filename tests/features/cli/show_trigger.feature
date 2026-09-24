Feature: Trigger show CLI
  As a MrMkt operator
  I want to show a stored trigger from the CLI
  So that errors are exact on the console

  Scenario: Show rejects an unknown name
    When I execute "mrmkt trigger show no-such-trigger"
    Then the command fails
    And the console displays:
      """
      Usage: root trigger show [OPTIONS] {name}
      Try 'root trigger show --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: no trigger with name 'no-such-trigger'                        │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """
