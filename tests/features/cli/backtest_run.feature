Feature: Backtest run with benchmark context
  As a MrMkt operator
  I want regime-gated strategies to receive a market benchmark
  So that gates apply without the benchmark becoming tradable

  Scenario: New strategy runs with an explicit benchmark kept non-tradable
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA --strategy trend-pullback --params market_sma=20,trend_sma=50,rising_bars=5,mom_lookback=60,mom_skip=5,momentum_top_share=1.0,pullback_period=10,recovery_bars=0,exit_mode=range --benchmark SPY"
    Then the command succeeds
    And the output mentions "Symbols: 1"
    And the output mentions "Trades:"

  Scenario: Explicitly selected benchmark is excluded from tradables
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA SPY --strategy trend-pullback --params market_sma=20,trend_sma=50,rising_bars=5,mom_lookback=60,mom_skip=5,momentum_top_share=1.0,pullback_period=10,recovery_bars=0,exit_mode=range --benchmark SPY"
    Then the command succeeds
    And the output mentions "Benchmark SPY excluded from tradable symbols."
    And the output mentions "Symbols: 1"

  Scenario: Fees flow through to the run
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA --strategy trend-pullback --params market_sma=20,trend_sma=50,rising_bars=5,mom_lookback=60,mom_skip=5,momentum_top_share=1.0,pullback_period=10,recovery_bars=0,exit_mode=range --benchmark SPY --fees 0.001"
    Then the command succeeds
    And the output mentions "Expectancy:"

  Scenario: Sole benchmark symbol stays tradable
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar rise-then-fall for SPY
    When I execute "mrmkt backtest run SPY --strategy sma-cross --params fast_period=5,slow_period=20 --from 2022-02-01 --benchmark SPY"
    Then the command succeeds
    And the output mentions "sole selected symbol"
    And the output mentions "Trades:"

  Scenario: Fill lag flag selects the execution model
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA --strategy trend-pullback --params market_sma=20,trend_sma=50,rising_bars=5,mom_lookback=60,mom_skip=5,momentum_top_share=1.0,pullback_period=10,recovery_bars=0,exit_mode=range --benchmark SPY --fill-lag 0"
    Then the command succeeds
    And the output mentions "Trades:"

  Scenario: Bad fill lag names the valid choices
    When I execute "mrmkt backtest run AAPL --fill-lag 5"
    Then the command fails
    And the output mentions "fill-lag"

  Scenario: Limit-touch fills only touched resting limits
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA --strategy buy-red --params use_vov=false --benchmark SPY --fill-model limit-touch"
    Then the command succeeds
    And the output mentions "Trades:"
    And the output mentions "Execution: fill-lag 1, fill-model limit-touch"

  Scenario: Limit fill price fills resting limits at the limit
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA --strategy buy-red --params use_vov=false --benchmark SPY --fill-model limit-touch --fill-price limit"
    Then the command succeeds
    And the output mentions "Trades:"
    And the output mentions "fill-price limit"

  Scenario: Bad fill price names the valid choices
    When I execute "mrmkt backtest run AAPL --fill-price midpoint"
    Then the command fails
    And the output mentions "fill-price"

  Scenario: Limit-touch without strategy limits is rejected
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    When I execute "mrmkt backtest run AAA --strategy trend-pullback --params market_sma=20,trend_sma=50,rising_bars=5,mom_lookback=60,mom_skip=5,momentum_top_share=1.0,pullback_period=10,recovery_bars=0,exit_mode=range --benchmark SPY --fill-model limit-touch"
    Then the command fails
    And the output mentions "entry limits"

  Scenario: Bad fill model names the valid choices
    When I execute "mrmkt backtest run AAPL --fill-model midpoint"
    Then the command fails
    And the output mentions "fill-model"

  Scenario: External strategy file runs through the CLI
    Given the local ticker catalog contains these symbols:
      | symbol | exchange | type      |
      | AAA    | NASDAQ   | us_equity |
      | SPY    | ARCA     | us_equity |
    And the local price catalog contains a 400-bar climb with a dip for AAA
    And the local price catalog contains a 400-bar steady climb for SPY
    And a strategy file defining "file-dip"
    When I execute "mrmkt backtest run AAA --strategy-file STRATEGY_FILE --strategy file-dip --benchmark SPY"
    Then the command succeeds
    And the output mentions "Trades:"
