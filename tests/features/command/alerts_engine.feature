Feature: Alert engine use case
  As a MrMkt operator
  I want transition-only triggers with explicit session and expiry rules
  So that notifications fire once per crossing and never silently

  Scenario: A touch fires once, repeats stay silent until re-arm
    Given an engine watching "AAA" at level 100.0 seeded above
    When "AAA" prints 99.0 in the regular session
    Then 1 alert fires
    When "AAA" prints 98.0 in the regular session
    Then 1 alerts have fired in total
    When "AAA" prints 101.0 in the regular session
    And "AAA" prints 99.5 in the regular session
    Then 2 alerts have fired in total

  Scenario: An opening gap across the level fires on the first print
    Given an engine watching "AAA" at level 100.0 seeded above
    When "AAA" prints 99.0 in the regular session
    Then 1 alert fires

  Scenario: A pre-session dip is recorded as ignored, never silent
    Given an engine watching "AAA" at level 100.0 seeded above
    When "AAA" prints 99.0 in the pre session
    Then 0 alerts fire
    And 1 tick is recorded ignored in the pre session

  Scenario: An expired trigger never fires
    Given an engine watching "AAA" at level 100.0 seeded above expiring yesterday
    When "AAA" prints 99.0 in the regular session
    Then 0 alerts fire
    And 1 tick is recorded ignored as expired

  Scenario: A crossing-up trigger fires on the rise through
    Given an engine watching "AAA" at level 100.0 from below with operator crossing-up
    When "AAA" prints 101.0 in the regular session
    Then 1 alert fires

  Scenario: Session boundaries respect daylight saving time
    Given an engine watching "AAA" at level 100.0 seeded above
    When "AAA" prints 99.0 at 2026-07-01 13:30 UTC
    Then 1 alert fires
    When "AAA" prints 101.0 at 2026-07-01 13:31 UTC
    And "AAA" prints 99.0 at 2026-07-01 13:29 UTC
    Then 1 alerts have fired in total
    And 1 tick is recorded ignored in the pre session

  Scenario: A seeded-below start needs a recross
    Given an engine watching "AAA" at level 100.0 seeded below
    When "AAA" prints 98.0 in the regular session
    Then 0 alerts fire
    When "AAA" prints 101.0 in the regular session
    And "AAA" prints 99.0 in the regular session
    Then 1 alerts have fired in total

  Scenario: A bad session policy is rejected
    When I build an engine with session policy "always"
    Then engine construction fails

  Scenario: A new daily bar recomputes the level
    Given an engine with 40 closes of history for "AAA" at 100.0
    When a new daily bar closes at 130.0
    Then the buy level changes
    When a tick between the old and new level still fires on the cross
    Then 1 alert fires

  Scenario: A level move reseeds the armed state
    Given an engine with 40 closes of history for "AAA" at 50.0
    And the trigger level is 48.0 seeded from 49.0
    When a new daily bar closes at 60.0
    Then the symbol is armed
    When "AAA" prints 45.0 in the regular session
    Then 1 alert fires

  Scenario: The exchange timestamp drives the session, not receipt time
    Given an engine watching "AAA" at level 100.0 seeded above
    When a trade prints 99.0 stamped pre-market but received mid-session
    Then 0 alerts fire
    And 1 tick is recorded ignored in the pre session

  Scenario: A missing trade timestamp falls back to the clock
    Given an engine watching "AAA" at level 100.0 seeded above
    When a trade prints 99.0 with no timestamp at mid-session receipt
    Then 1 alert fires

  Scenario: File sink appends trigger lines
    Given an engine watching "AAA" at level 100.0 seeded above
    When "AAA" prints 99.0 in the regular session into a temp file
    Then the temp file holds a TRIGGER line for "AAA"

  Scenario: Ntfy posts raw text with title and priority
    Given an engine watching "CPAY" at level 390.07 seeded above
    When "CPAY" prints 390.0 in the regular session to ntfy
    Then ntfy receives a POST with title "CPAY below risk-range buy 390.07" and priority "4"

  Scenario: Ntfy failures never log the topic
    Given an engine watching "AAA" at level 100.0 seeded above
    When "AAA" prints 99.0 in the regular session to a failing ntfy
    Then 0 alerts are lost and stderr hides the topic

  Scenario: Ntfy URL resolves env first, then config spellings
    When I resolve the ntfy URL from env and config variants
    Then env wins over config and both ntfy spellings resolve

  Scenario: Levels are deterministic across runs
    Given stored bars for "AAA" with a late dip below its range
    When I compute levels twice
    Then both levels CSVs are identical
    And the range low sits below the close

  Scenario: A once trigger never rearms
    Given an engine watching "AAA" at level 100.0 seeded above with frequency once
    When "AAA" prints 99.0 in the regular session
    Then 1 alert fires
    When "AAA" prints 101.0 in the regular session
    And "AAA" prints 99.0 in the regular session
    Then 1 alerts have fired in total

  Scenario: Every-time fires each holding tick
    Given an engine watching "AAA" at level 100.0 from below with operator greater-than and frequency every_time
    When "AAA" prints 101.0 in the regular session
    And "AAA" prints 102.0 in the regular session
    Then 2 alerts have fired in total

  Scenario: A message template renders placeholders
    Given an engine watching "AAA" at level 100.0 seeded above with message "{symbol} ping"
    When "AAA" prints 99.0 in the regular session
    Then the fired alert text is "AAA ping"

  Scenario: A bad template falls back to the default line
    Given an engine watching "AAA" at level 100.0 seeded above with message "{nonexistent}"
    When "AAA" prints 99.0 in the regular session
    Then the fired alert line holds TRIGGER

  Scenario: Dry-run replays causally with no sink contact
    Given stored bars for "AAA" with a late dip below its range
    When I dry-run the replay
    Then every fired alert has price at or below its level
    And delivery happened only through on_alert
