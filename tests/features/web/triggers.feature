Feature: Trigger web fragment
  As a MrMkt operator
  I want to browse stored triggers in a browser
  So that trigger state is visible without the CLI

  Scenario: Fragment lists stored triggers
    Given trigger "dip-watch" exists
    When I open "/fragments/triggers"
    Then the web command succeeds
    And the trigger fragment lists "dip-watch"

  Scenario: Fragment reports an empty trigger catalog
    When I open "/fragments/triggers"
    Then the web command succeeds
    And the fragment says no triggers were found

  Scenario: Index page opens on the chart with triggers
    When I open "/"
    Then the web command succeeds
    And the index opens on the S&P 500 chart
    And the index references the triggers fragment
