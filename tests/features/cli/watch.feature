Feature: Watch CLI argument forwarding
  As a MrMkt operator
  I want mrmkt watch to pass its arguments to the watch command
  So that CLI output reflects the requested selection

  Scenario: Watch forwards explicit symbols
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | BBB    | NASDAQ   | us_equity |
    And AAA has a 60-bar climb with a dip
    And BBB has a 5-bar climb
    When I execute "mrmkt watch AAA BBB --dry-run"
    Then the command succeeds
    And the output is:
      """
      # dry-run: replaying stored daily lows as regular-session ticks; sinks not called
      would alert: 2022-02-14T15:59:00-05:00 | regular | AAA | 105.116 <= buy 105.543 TRIGGER
      would alert: 2022-02-15T15:59:00-05:00 | regular | AAA | 105.326 <= buy 105.754 TRIGGER
      would alert: 2022-02-16T15:59:00-05:00 | regular | AAA | 105.536 <= buy 105.966 TRIGGER
      would alert: 2022-02-17T15:59:00-05:00 | regular | AAA | 105.747 <= buy 106.178 TRIGGER
      would alert: 2022-02-18T15:59:00-05:00 | regular | AAA | 105.959 <= buy 106.39 TRIGGER
      would alert: 2022-02-21T15:59:00-05:00 | regular | AAA | 106.171 <= buy 106.603 TRIGGER
      would alert: 2022-02-22T15:59:00-05:00 | regular | AAA | 106.383 <= buy 106.816 TRIGGER
      would alert: 2022-02-23T15:59:00-05:00 | regular | AAA | 106.596 <= buy 107.03 TRIGGER
      would alert: 2022-02-24T15:59:00-05:00 | regular | AAA | 106.809 <= buy 107.244 TRIGGER
      would alert: 2022-02-25T15:59:00-05:00 | regular | AAA | 107.023 <= buy 107.458 TRIGGER
      would alert: 2022-02-28T15:59:00-05:00 | regular | AAA | 107.237 <= buy 107.673 TRIGGER
      would alert: 2022-03-01T15:59:00-05:00 | regular | AAA | 107.451 <= buy 107.888 TRIGGER
      would alert: 2022-03-02T15:59:00-05:00 | regular | AAA | 107.666 <= buy 108.104 TRIGGER
      would alert: 2022-03-03T15:59:00-05:00 | regular | AAA | 107.882 <= buy 108.32 TRIGGER
      would alert: 2022-03-04T15:59:00-05:00 | regular | AAA | 108.097 <= buy 108.537 TRIGGER
      would alert: 2022-03-07T15:59:00-05:00 | regular | AAA | 97.4822 <= buy 108.754 TRIGGER
      """

  Scenario: Watch forwards --indicator
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt watch AAA --dry-run --indicator risk-range"
    Then the command succeeds
    And the output is:
      """
      # dry-run: replaying stored daily lows as regular-session ticks; sinks not called
      would alert: 2022-02-14T15:59:00-05:00 | regular | AAA | 105.116 <= buy 105.543 TRIGGER
      would alert: 2022-02-15T15:59:00-05:00 | regular | AAA | 105.326 <= buy 105.754 TRIGGER
      would alert: 2022-02-16T15:59:00-05:00 | regular | AAA | 105.536 <= buy 105.966 TRIGGER
      would alert: 2022-02-17T15:59:00-05:00 | regular | AAA | 105.747 <= buy 106.178 TRIGGER
      would alert: 2022-02-18T15:59:00-05:00 | regular | AAA | 105.959 <= buy 106.39 TRIGGER
      would alert: 2022-02-21T15:59:00-05:00 | regular | AAA | 106.171 <= buy 106.603 TRIGGER
      would alert: 2022-02-22T15:59:00-05:00 | regular | AAA | 106.383 <= buy 106.816 TRIGGER
      would alert: 2022-02-23T15:59:00-05:00 | regular | AAA | 106.596 <= buy 107.03 TRIGGER
      would alert: 2022-02-24T15:59:00-05:00 | regular | AAA | 106.809 <= buy 107.244 TRIGGER
      would alert: 2022-02-25T15:59:00-05:00 | regular | AAA | 107.023 <= buy 107.458 TRIGGER
      would alert: 2022-02-28T15:59:00-05:00 | regular | AAA | 107.237 <= buy 107.673 TRIGGER
      would alert: 2022-03-01T15:59:00-05:00 | regular | AAA | 107.451 <= buy 107.888 TRIGGER
      would alert: 2022-03-02T15:59:00-05:00 | regular | AAA | 107.666 <= buy 108.104 TRIGGER
      would alert: 2022-03-03T15:59:00-05:00 | regular | AAA | 107.882 <= buy 108.32 TRIGGER
      would alert: 2022-03-04T15:59:00-05:00 | regular | AAA | 108.097 <= buy 108.537 TRIGGER
      would alert: 2022-03-07T15:59:00-05:00 | regular | AAA | 97.4822 <= buy 108.754 TRIGGER
      """

  Scenario: Watch forwards --tag
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt watch --tag universe --dry-run"
    Then the command succeeds
    And the output is:
      """
      # dry-run: replaying stored daily lows as regular-session ticks; sinks not called
      would alert: 2022-02-14T15:59:00-05:00 | regular | AAA | 105.116 <= buy 105.543 TRIGGER
      would alert: 2022-02-15T15:59:00-05:00 | regular | AAA | 105.326 <= buy 105.754 TRIGGER
      would alert: 2022-02-16T15:59:00-05:00 | regular | AAA | 105.536 <= buy 105.966 TRIGGER
      would alert: 2022-02-17T15:59:00-05:00 | regular | AAA | 105.747 <= buy 106.178 TRIGGER
      would alert: 2022-02-18T15:59:00-05:00 | regular | AAA | 105.959 <= buy 106.39 TRIGGER
      would alert: 2022-02-21T15:59:00-05:00 | regular | AAA | 106.171 <= buy 106.603 TRIGGER
      would alert: 2022-02-22T15:59:00-05:00 | regular | AAA | 106.383 <= buy 106.816 TRIGGER
      would alert: 2022-02-23T15:59:00-05:00 | regular | AAA | 106.596 <= buy 107.03 TRIGGER
      would alert: 2022-02-24T15:59:00-05:00 | regular | AAA | 106.809 <= buy 107.244 TRIGGER
      would alert: 2022-02-25T15:59:00-05:00 | regular | AAA | 107.023 <= buy 107.458 TRIGGER
      would alert: 2022-02-28T15:59:00-05:00 | regular | AAA | 107.237 <= buy 107.673 TRIGGER
      would alert: 2022-03-01T15:59:00-05:00 | regular | AAA | 107.451 <= buy 107.888 TRIGGER
      would alert: 2022-03-02T15:59:00-05:00 | regular | AAA | 107.666 <= buy 108.104 TRIGGER
      would alert: 2022-03-03T15:59:00-05:00 | regular | AAA | 107.882 <= buy 108.32 TRIGGER
      would alert: 2022-03-04T15:59:00-05:00 | regular | AAA | 108.097 <= buy 108.537 TRIGGER
      would alert: 2022-03-07T15:59:00-05:00 | regular | AAA | 97.4822 <= buy 108.754 TRIGGER
      """

  Scenario: Watch forwards --trigger-id
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    When I execute "mrmkt watch --trigger-id 1 --dry-run"
    Then the command succeeds
    And the output is:
      """
      # dry-run: replaying stored daily lows as regular-session ticks; sinks not called
      would alert: 2022-02-14T15:59:00-05:00 | regular | AAA | 105.116 <= buy 105.543 TRIGGER
      would alert: 2022-02-15T15:59:00-05:00 | regular | AAA | 105.326 <= buy 105.754 TRIGGER
      would alert: 2022-02-16T15:59:00-05:00 | regular | AAA | 105.536 <= buy 105.966 TRIGGER
      would alert: 2022-02-17T15:59:00-05:00 | regular | AAA | 105.747 <= buy 106.178 TRIGGER
      would alert: 2022-02-18T15:59:00-05:00 | regular | AAA | 105.959 <= buy 106.39 TRIGGER
      would alert: 2022-02-21T15:59:00-05:00 | regular | AAA | 106.171 <= buy 106.603 TRIGGER
      would alert: 2022-02-22T15:59:00-05:00 | regular | AAA | 106.383 <= buy 106.816 TRIGGER
      would alert: 2022-02-23T15:59:00-05:00 | regular | AAA | 106.596 <= buy 107.03 TRIGGER
      would alert: 2022-02-24T15:59:00-05:00 | regular | AAA | 106.809 <= buy 107.244 TRIGGER
      would alert: 2022-02-25T15:59:00-05:00 | regular | AAA | 107.023 <= buy 107.458 TRIGGER
      would alert: 2022-02-28T15:59:00-05:00 | regular | AAA | 107.237 <= buy 107.673 TRIGGER
      would alert: 2022-03-01T15:59:00-05:00 | regular | AAA | 107.451 <= buy 107.888 TRIGGER
      would alert: 2022-03-02T15:59:00-05:00 | regular | AAA | 107.666 <= buy 108.104 TRIGGER
      would alert: 2022-03-03T15:59:00-05:00 | regular | AAA | 107.882 <= buy 108.32 TRIGGER
      would alert: 2022-03-04T15:59:00-05:00 | regular | AAA | 108.097 <= buy 108.537 TRIGGER
      would alert: 2022-03-07T15:59:00-05:00 | regular | AAA | 97.4822 <= buy 108.754 TRIGGER
      """

  Scenario: Watch forwards --all-triggers
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    When I execute "mrmkt watch --all-triggers --dry-run"
    Then the command succeeds
    And the output is:
      """
      # dry-run: replaying stored daily lows as regular-session ticks; sinks not called
      would alert: 2022-02-14T15:59:00-05:00 | regular | AAA | 105.116 <= buy 105.543 TRIGGER
      would alert: 2022-02-15T15:59:00-05:00 | regular | AAA | 105.326 <= buy 105.754 TRIGGER
      would alert: 2022-02-16T15:59:00-05:00 | regular | AAA | 105.536 <= buy 105.966 TRIGGER
      would alert: 2022-02-17T15:59:00-05:00 | regular | AAA | 105.747 <= buy 106.178 TRIGGER
      would alert: 2022-02-18T15:59:00-05:00 | regular | AAA | 105.959 <= buy 106.39 TRIGGER
      would alert: 2022-02-21T15:59:00-05:00 | regular | AAA | 106.171 <= buy 106.603 TRIGGER
      would alert: 2022-02-22T15:59:00-05:00 | regular | AAA | 106.383 <= buy 106.816 TRIGGER
      would alert: 2022-02-23T15:59:00-05:00 | regular | AAA | 106.596 <= buy 107.03 TRIGGER
      would alert: 2022-02-24T15:59:00-05:00 | regular | AAA | 106.809 <= buy 107.244 TRIGGER
      would alert: 2022-02-25T15:59:00-05:00 | regular | AAA | 107.023 <= buy 107.458 TRIGGER
      would alert: 2022-02-28T15:59:00-05:00 | regular | AAA | 107.237 <= buy 107.673 TRIGGER
      would alert: 2022-03-01T15:59:00-05:00 | regular | AAA | 107.451 <= buy 107.888 TRIGGER
      would alert: 2022-03-02T15:59:00-05:00 | regular | AAA | 107.666 <= buy 108.104 TRIGGER
      would alert: 2022-03-03T15:59:00-05:00 | regular | AAA | 107.882 <= buy 108.32 TRIGGER
      would alert: 2022-03-04T15:59:00-05:00 | regular | AAA | 108.097 <= buy 108.537 TRIGGER
      would alert: 2022-03-07T15:59:00-05:00 | regular | AAA | 97.4822 <= buy 108.754 TRIGGER
      """

  Scenario: Bare watch forwards an empty selection
    Given the alerts catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
    And each alerts symbol has a 60-bar climb with a dip tagged universe
    When I execute "mrmkt trigger create dip-watch --symbol AAA --operator crossing-down --indicator risk-range"
    Then the command succeeds
    When I execute "mrmkt watch --dry-run"
    Then the command succeeds
    And the output is:
      """
      # dry-run: replaying stored daily lows as regular-session ticks; sinks not called
      would alert: 2022-02-14T15:59:00-05:00 | regular | AAA | 105.116 <= buy 105.543 TRIGGER
      would alert: 2022-02-15T15:59:00-05:00 | regular | AAA | 105.326 <= buy 105.754 TRIGGER
      would alert: 2022-02-16T15:59:00-05:00 | regular | AAA | 105.536 <= buy 105.966 TRIGGER
      would alert: 2022-02-17T15:59:00-05:00 | regular | AAA | 105.747 <= buy 106.178 TRIGGER
      would alert: 2022-02-18T15:59:00-05:00 | regular | AAA | 105.959 <= buy 106.39 TRIGGER
      would alert: 2022-02-21T15:59:00-05:00 | regular | AAA | 106.171 <= buy 106.603 TRIGGER
      would alert: 2022-02-22T15:59:00-05:00 | regular | AAA | 106.383 <= buy 106.816 TRIGGER
      would alert: 2022-02-23T15:59:00-05:00 | regular | AAA | 106.596 <= buy 107.03 TRIGGER
      would alert: 2022-02-24T15:59:00-05:00 | regular | AAA | 106.809 <= buy 107.244 TRIGGER
      would alert: 2022-02-25T15:59:00-05:00 | regular | AAA | 107.023 <= buy 107.458 TRIGGER
      would alert: 2022-02-28T15:59:00-05:00 | regular | AAA | 107.237 <= buy 107.673 TRIGGER
      would alert: 2022-03-01T15:59:00-05:00 | regular | AAA | 107.451 <= buy 107.888 TRIGGER
      would alert: 2022-03-02T15:59:00-05:00 | regular | AAA | 107.666 <= buy 108.104 TRIGGER
      would alert: 2022-03-03T15:59:00-05:00 | regular | AAA | 107.882 <= buy 108.32 TRIGGER
      would alert: 2022-03-04T15:59:00-05:00 | regular | AAA | 108.097 <= buy 108.537 TRIGGER
      would alert: 2022-03-07T15:59:00-05:00 | regular | AAA | 97.4822 <= buy 108.754 TRIGGER
      """
