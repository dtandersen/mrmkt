Feature: Live price watch
  As a MrMkt operator
  I want live prices analyzed against stored levels
  So that trigger hits are printed to the console

  Scenario: Bare watch selects every enabled stored trigger
    Given AAA has a 60-bar climb with a dip
    And stored trigger "dip-watch" watches "AAA" crossing down
    When I watch with no selection in live mode
    Then the watch succeeds
    And the price source receives symbols "AAA"
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-03-25.
      """

  Scenario: Bare watch with no enabled triggers reports an empty store
    Given AAA has a 60-bar steady climb
    When I watch with no selection in live mode
    Then the watch succeeds
    And the emitted lines are:
      """
      No enabled triggers in the store.
      """

  Scenario: Explicit symbols select only symbols with enough history
    Given AAA has a 60-bar climb with a dip
    And BBB has a 5-bar climb
    When I watch symbols "AAA" and "BBB" in live mode
    Then the watch succeeds
    And the price source receives symbols "AAA"

  Scenario: Symbols and stored triggers cannot be mixed
    Given AAA has a 60-bar climb with a dip
    And stored trigger "dip-watch" watches "AAA" crossing down
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
    Given AAA has a 60-bar climb with a dip
    When I stream an above-level quote then a below-level quote
    Then the watch succeeds
    And the emitted lines are:
      """
      Watching 1 symbols (regular sessions fire); levels as of 2022-03-25.
      2022-04-04T10:02:00-04:00 | regular | AAA | 105 <= buy 106.144 TRIGGER
      """

  Scenario: A once trigger is disabled after a live hit
    Given AAA has a 60-bar climb with a dip
    And stored trigger "once-watch" watches "AAA" crossing down once
    When I stream an above-level quote then a below-level quote
    Then the watch succeeds
    And the stored trigger is disabled

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
