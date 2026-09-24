Feature: Current signal discovery use case
  As a MrMkt operator
  I want per-symbol strategy signals at a stored bar
  So that candidates carry their ranking inputs without implying fills

  Scenario: Buy-red rows carry rank inputs and never imply a fill
    Given a clean price catalog
    And symbol "AAA" has a 300-bar climb tagged "universe"
    And symbol "BBB" has a 300-bar flat line tagged "universe"
    When I score strategy "buy-red" on tag "universe"
    Then every row has a signal date on or before as-of
    And row "AAA" reports dist_lo, drawdown, and trend state
    And the CSV states no fill price is shown or implied

  Scenario: Trend-pullback rows carry momentum rank and gate state
    Given a clean price catalog
    And symbol "AAA" has a 300-bar climb tagged "universe"
    And symbol "BBB" has a 300-bar flat line tagged "universe"
    When I score strategy "trend-pullback" with momentum_top_share 1.0 on tag "universe"
    Then every row reports momentum value, momentum rank, and gate

  Scenario: The benchmark is context, never a candidate
    Given a clean price catalog
    And symbol "AAA" has a 300-bar climb tagged "universe"
    And symbol "SPY" has a 300-bar climb tagged "universe"
    When I score strategy "sma-cross" on tag "universe" with benchmark "SPY"
    Then "SPY" is not a scored row
    And the CSV reports the benchmark resolved

  Scenario: The benchmark can opt back into candidates
    Given a clean price catalog
    And symbol "AAA" has a 300-bar climb tagged "universe"
    And symbol "SPY" has a 300-bar climb tagged "universe"
    When I score strategy "sma-cross" on tag "universe" with benchmark "SPY" included
    Then "SPY" is a scored row

  Scenario: Signal CSV numerics parse as floats
    Given a clean price catalog
    And symbol "AAA" has a 300-bar climb tagged "universe"
    When I score strategy "buy-red" on tag "universe"
    Then every non-empty numeric cell parses as float

  Scenario: A missing benchmark falls back transparently
    Given a clean price catalog
    And symbol "AAA" has a 300-bar climb tagged "universe"
    When I score strategy "sma-cross" on tag "universe" with benchmark "SPY"
    Then the CSV reports the benchmark missing with fallback
