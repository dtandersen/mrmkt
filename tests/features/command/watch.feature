Feature: Live price watch
  As a MrMkt operator
  I want live prices analyzed against stored levels
  So that trigger hits are printed to the console

  Background:
    Given the daily price history of AAA from 2022-01-03 to 2022-02-14 rising 0.2 per day

  Scenario: Bare watch selects every enabled stored trigger
    Given the stored triggers:
      | name      | symbol | indicator  | operator      | value | frequency      | expires_at | message | enabled |
      | dip-watch | AAA    | risk-range | crossing-down |       | once_per_rearm |            |         | true    |
    And the real time quotes:
      | symbol | timestamp                 | bid | ask |
      | AAA    | 2022-04-04T10:00:00-04:00 | 110 | 111 |
      | AAA    | 2022-04-04T10:01:00-04:00 | 105 | 107 |
      | AAA    | 2022-04-04T10:02:00-04:00 | 104 | 105 |
    When I watch with no selection in live mode
    Then the watch succeeds
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      Trigger fired: dip-watch
      symbol: AAA, bid: 104, ask: 105
      """

  Scenario: Bare watch with no enabled triggers reports an empty store
    When I watch with no selection in live mode
    Then the watch succeeds
    And the emitted lines are:
      """
      No enabled triggers in the store.
      """

  Scenario: Explicit symbols select only symbols with enough history
    Given the daily price history of BBB from 2022-01-03 to 2022-01-07 rising 1.0 per day
    When I watch symbols "AAA" and "BBB" in live mode
    Then the watch succeeds
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      """

  Scenario: Symbols and stored triggers cannot be mixed
    Given the stored triggers:
      | name      | symbol | indicator  | operator      | value | frequency      | expires_at | message | enabled |
      | dip-watch | AAA    | risk-range | crossing-down |       | once_per_rearm |            |         | true    |
    When I watch symbol "AAA" plus its stored trigger
    Then the watch errors are:
      """
      use either symbols or stored triggers, not both
      """

  Scenario: Unknown trigger id is rejected
    When I watch trigger id 999
    Then the watch errors are:
      """
      no enabled trigger with id [999]
      """

  Scenario: A live crossing prints the alert
    When I stream these quotes:
      | symbol | timestamp                 | bid | ask |
      | AAA    | 2022-04-04T10:00:00-04:00 | 110 | 111 |
      | AAA    | 2022-04-04T10:01:00-04:00 | 105 | 107 |
      | AAA    | 2022-04-04T10:02:00-04:00 | 104 | 105 |
    Then the watch succeeds
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      Trigger fired: AAA
      symbol: AAA, bid: 104, ask: 105
      """

  Scenario: A once trigger is disabled after a live hit
    Given the stored triggers:
      | name       | symbol | indicator  | operator      | value | frequency | expires_at | message | enabled |
      | once-watch | AAA    | risk-range | crossing-down |       | once      |            |         | true    |
    When I stream these quotes:
      | symbol | timestamp                 | bid | ask |
      | AAA    | 2022-04-04T10:00:00-04:00 | 110 | 111 |
      | AAA    | 2022-04-04T10:01:00-04:00 | 105 | 107 |
      | AAA    | 2022-04-04T10:02:00-04:00 | 104 | 105 |
    Then the watch succeeds
    And the stored trigger is disabled

  Scenario: Interrupting the stream stops watching cleanly
    Given the stored triggers:
      | name      | symbol | indicator  | operator      | value | frequency      | expires_at | message | enabled |
      | dip-watch | AAA    | risk-range | crossing-down |       | once_per_rearm |            |         | true    |
    When I watch with no selection and interrupt the stream
    Then the watch succeeds
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      Stopped watching.
      """

  Scenario: SIGINT stops a blocking watch cleanly
    Given a blocking watch is running in a child process
    When I send SIGINT to the child process
    Then the child exits with code 0
    And the child output is:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-02-14.
      Stopped watching.
      """
