Feature: Show stored fundamentals
  As a MrMkt operator
  I want one symbol's stored statements in deterministic order
  So that I can inspect what the import saved

  Scenario: Stored statements print oldest first
    Given a clean fundamentals store
    And stored fundamentals for "AAA" on "2024-03-31" and "2024-06-30"
    When I show fundamentals for "AAA"
    Then the show succeeds
    And the income dates are "2024-03-31,2024-06-30"

  Scenario: Unknown symbols are not found
    Given a clean fundamentals store
    When I show fundamentals for "ZZZ"
    Then the show fails naming "no fundamentals for 'ZZZ'"
