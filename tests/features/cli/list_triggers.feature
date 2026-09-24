Feature: Trigger list CLI
  As a MrMkt operator
  I want to list stored triggers from the CLI
  So that show, list, and delete output is exact on the console

  Scenario: Show, list, and delete round trip by name
    Given the trigger catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,signal,operator,value,frequency,expires_at,message,enabled
      dip-watch,AAA,risk-range,crossing-down,,once_per_rearm,,,true
      """
    When I execute "mrmkt trigger show dip-watch"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,signal,operator,value,frequency,expires_at,message,enabled
      dip-watch,AAA,risk-range,crossing-down,,once_per_rearm,,,true
      """
    When I execute "mrmkt trigger list"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,signal,operator,value,frequency,expires_at,message,enabled
      dip-watch,AAA,risk-range,crossing-down,,once_per_rearm,,,true
      """
    When I execute "mrmkt trigger delete dip-watch"
    Then the command succeeds
    And the console displays:
      """
      deleted trigger dip-watch
      """
    When I execute "mrmkt trigger list"
    Then the command succeeds
    And the console displays:
      """
      # generator=mrmkt trigger list
      name,symbol,signal,operator,value,frequency,expires_at,message,enabled
      """
