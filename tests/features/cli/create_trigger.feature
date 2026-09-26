Feature: Trigger create CLI
  As a MrMkt operator
  I want to store named realtime triggers from the CLI
  So that create output and errors are exact on the console

  Scenario: Create names the trigger explicitly
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,indicator,operator,value,frequency,expires_at,message,enabled
      dip-watch,AAA,risk-range,crossing-down,,once_per_rearm,,,true
      """

  Scenario: Create without a name defaults to trigger-123456
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And the generated trigger name is "trigger-123456"
    When I execute "mrmkt trigger create --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,indicator,operator,value,frequency,expires_at,message,enabled
      trigger-123456,AAA,risk-range,crossing-down,,once_per_rearm,,,true
      """

  Scenario: Create requires a symbol
    When I execute "mrmkt trigger create dip-watch --operator crossing-down --indicator risk-range"
    Then the command fails
    And the console displays:
      """
      Usage: root trigger create [OPTIONS] [name]
      Try 'root trigger create --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Missing option '--symbol'.                                                   │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """

  Scenario: Create rejects an unknown operator
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator sideways --indicator risk-range"
    Then the command fails
    And the console displays:
      """
      Usage: root trigger create [OPTIONS] [name]
      Try 'root trigger create --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: operator: 'sideways' is an invalid operator                   │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """

  Scenario: Create rejects a duplicate symbol and operator
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create first --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,indicator,operator,value,frequency,expires_at,message,enabled
      first,AAA,risk-range,crossing-down,,once_per_rearm,,,true
      """
    When I execute "mrmkt trigger create second --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command fails
    And the console displays:
      """
      Usage: root trigger create [OPTIONS] [name]
      Try 'root trigger create --help' for help.
      ╭─ Error ──────────────────────────────────────────────────────────────────────╮
      │ Invalid value: trigger already exists for AAA risk-range crossing-down       │
      ╰──────────────────────────────────────────────────────────────────────────────╯
      """
