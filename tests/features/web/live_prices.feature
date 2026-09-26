Feature: Live price event stream
  As a MrMkt operator
  I want live trade ticks as server-sent events
  So that the dashboard shows the current price without the CLI

  Scenario: Stream emits a live tick
    Given live ticks for these prints:
      | symbol | price  | at                  |
      | NVDA   | 150.25 | 2026-09-26T14:30:00 |
    When I open "/fragments/prices/live?symbol=NVDA"
    Then the web command succeeds
    And the live stream is an event stream
    And the live stream emits a tick
    And the live tick shows "NVDA"
    And the live tick shows "150.25"
    And the live tick shows "true"

  Scenario: Stream opens with the last stored bar when no ticks flow
    Given the local price catalog contains these daily bars:
      | symbol | date       | open | high | low | close | volume |
      | NVDA   | 2026-09-25 | 140  | 142  | 139 | 141.5 | 1000   |
    When I open "/fragments/prices/live?symbol=NVDA"
    Then the web command succeeds
    And the live stream emits a tick
    And the live tick shows "141.5"
    And the live tick shows "false"

  Scenario: Stream rejects an invalid symbol
    When I open "/fragments/prices/live?symbol=bad%20symbol"
    Then the web command fails with status 400
