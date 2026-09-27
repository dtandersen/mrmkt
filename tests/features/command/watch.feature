Feature: Watch prices use case
  As a MrMkt operator
  I want the watch command to stream stored triggers and report crossings
  So that live monitoring works without CLI wiring

  Scenario: Bare watch defaults to all stored triggers
    Given AAA has a 60-bar climb with a dip
    And stored trigger "dip-watch" watches "AAA" crossing down
    When I watch with no selection in dry-run mode
    Then the watch succeeds
    And the emitted lines are:
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

  Scenario: Bare watch with no stored triggers reports empty store
    Given AAA has a 60-bar steady climb
    When I watch with no selection in dry-run mode
    Then the watch succeeds
    And the emitted lines are:
      """
      No enabled triggers in the store.
      """

  Scenario: Explicit symbols scope a dry-run
    Given AAA has a 60-bar climb with a dip
    And BBB has a 5-bar climb
    When I watch symbols "AAA" and "BBB" in dry-run mode
    Then the watch succeeds
    And the emitted lines are:
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

  Scenario: Mixing symbols with stored triggers is rejected
    Given AAA has a 60-bar climb with a dip
    And stored trigger "dip-watch" watches "AAA" crossing down
    When I watch symbol "AAA" plus its stored trigger in dry-run mode
    Then the watch errors are:
      """
      use either symbols/--tag or stored triggers, not both
      """

  Scenario: An unknown trigger id is rejected
    Given AAA has a 60-bar steady climb
    When I watch trigger id 999 in dry-run mode
    Then the watch errors are:
      """
      no enabled trigger with id [999]
      """

  Scenario: A bad session policy is rejected
    Given AAA has a 60-bar steady climb
    When I watch symbol "AAA" with session policy "bogus" in dry-run mode
    Then the watch errors are:
      """
      --session-policy must be regular or extended
      """

  Scenario: An unknown sink is rejected
    Given AAA has a 60-bar steady climb
    When I watch symbol "AAA" with sink "carrier-pigeon" in dry-run mode
    Then the watch errors are:
      """
      unknown sink 'carrier-pigeon' (choose stdout, file, ntfy)
      """

  Scenario: An invalid indicator is rejected
    Given AAA has a 60-bar steady climb
    When I watch symbol "AAA" with indicator "bogus!" in dry-run mode
    Then the watch errors are:
      """
      'bogus!' is an invalid indicator (use letters, numbers, '-' or '_')
      """

  Scenario: Live watch hands trigger symbols to the stream runner
    Given AAA has a 60-bar climb with a dip
    And stored trigger "dip-watch" watches "AAA" crossing down
    When I watch with no selection in live mode
    Then the watch succeeds
    And the stream runner receives symbols "AAA"
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-03-25.
      """

  Scenario: Interrupting the stream stops watching cleanly
    Given AAA has a 60-bar climb with a dip
    And stored trigger "dip-watch" watches "AAA" crossing down
    When I watch with no selection and interrupt the stream
    Then the watch succeeds
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-03-25.
      Stopped watching.
      """

  Scenario: SIGINT stops a blocking watch cleanly
    Given a blocking watch is running in a child process
    When I send SIGINT to the child process
    Then the child exits with code 0
    And the child output is:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-03-25.
      Stopped watching.
      """

  Scenario: Live ticks firing a crossing deliver to the sink
    Given AAA has a 60-bar climb with a dip
    When I stream an above-level tick then a below-level tick in live mode
    Then the watch succeeds
    And the sink file contains:
      """
      2022-04-04T10:01:00-04:00 | regular | AAA | 1e-06 <= buy 106.144 TRIGGER
      """
