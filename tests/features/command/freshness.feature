Feature: Price freshness use case
  As a MrMkt operator
  I want staleness and bar-quality flags over stored bars
  So that screens run on data whose limits are explicit

  Scenario: A stale symbol is flagged with its last bar
    Given a clean price catalog
    And symbol "OLD" has 30 daily bars ending 10 days before today
    When I check freshness today
    Then "OLD" is flagged "STALE" with staleness 10 days

  Scenario: Bad bars and zero volume are flagged
    Given a clean price catalog
    And symbol "BAD" has a bar with high below low and a bar with zero volume
    When I check freshness today
    Then "BAD" is flagged "OHLC_VIOLATION"
    And "BAD" is flagged "ZERO_VOLUME"

  Scenario: Overnight gaps stay explicitly heuristic
    Given a clean price catalog
    And symbol "GAP" halves overnight once
    When I check freshness today
    Then "GAP" is flagged "GAP_JUMP_HEURISTIC"
    And the CSV calls the flags suspicion heuristics with no adjustment provenance

  Scenario: Symbols without bars are reported, not dropped
    Given a clean price catalog
    And symbol "EMPTY" has a catalog entry but no bars
    When I check freshness today
    Then "EMPTY" is flagged "NO_BARS"
