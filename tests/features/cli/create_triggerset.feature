Feature: Triggerset create CLI
  As a MrMkt operator
  I want to create trigger sets from the CLI
  So that set-create output and errors are exact on the console

  Scenario: Triggerset create without a name defaults to triggerset-123456
    Given the generated trigger set name is "triggerset-123456"
    When I execute "mrmkt triggerset create"
    Then the command succeeds
    And the console displays:
      """
      created trigger set triggerset-123456
      """

  Scenario: Triggerset create rejects a duplicate name
    When I execute "mrmkt triggerset create my-set"
    Then the command succeeds
    And the console displays:
      """
      created trigger set my-set
      """
    When I execute "mrmkt triggerset create my-set"
    Then the command fails
    And the console displays:
      """
      Usage: root triggerset create [OPTIONS] [name]
      Try 'root triggerset create --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: trigger set 'my-set' already exists                           │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """
