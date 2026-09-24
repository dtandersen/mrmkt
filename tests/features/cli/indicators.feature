Feature: Calculate indicators over stored prices
  As a MrMkt operator
  I want to calculate indicators over a symbol's stored price history
  So that I can inspect indicator values through time

  Scenario: Calculate an SMA with price history before the output range as warm-up
    Given the local price catalog contains these daily bars:
      | symbol | date       | close |
      | AAPL   | 2024-01-01 | 100   |
      | AAPL   | 2024-01-02 | 102   |
      | AAPL   | 2024-01-03 | 104   |
      | AAPL   | 2024-01-04 | 106   |
    When I execute "mrmkt indicators sma AAPL --period 3 --from 2024-01-03 --to 2024-01-04"
    Then the command succeeds
    And the indicator output has column "SMA_3D" and these values:
      | date       | close | value |
      | 2024-01-03 | 104   | 102   |
      | 2024-01-04 | 106   | 104   |

  Scenario: Calculate annualized volatility from daily log returns
    Given the local price catalog contains these daily bars:
      | symbol | date       | close |
      | AAPL   | 2024-01-01 | 100   |
      | AAPL   | 2024-01-02 | 110   |
      | AAPL   | 2024-01-03 | 110   |
      | AAPL   | 2024-01-04 | 132   |
    When I execute "mrmkt indicators volatility AAPL --period 2 --from 2024-01-03 --to 2024-01-04"
    Then the command succeeds
    And the indicator output has column "VOL_2D" and these values:
      | date       | close | value   |
      | 2024-01-03 | 110   | 1.06985 |
      | 2024-01-04 | 132   | 2.04655 |

  Scenario: Calculate volatility of volatility over log changes in realized volatility
    Given the local price catalog contains these daily bars:
      | symbol | date       | close |
      | AAPL   | 2024-01-01 | 100   |
      | AAPL   | 2024-01-02 | 110   |
      | AAPL   | 2024-01-03 | 110   |
      | AAPL   | 2024-01-04 | 132   |
      | AAPL   | 2024-01-05 | 145.2 |
    When I execute "mrmkt indicators vol-of-vol AAPL --vol-period 2 --vov-period 2 --from 2024-01-05 --to 2024-01-05"
    Then the command succeeds
    And the indicator output has column "VOV_2D_2D" and these values:
      | date       | close | value   |
      | 2024-01-05 | 145.2 | 0.981725 |

  Scenario: Calculate a separate rolling percentile of realized volatility
    Given the local price catalog contains these daily bars:
      | symbol | date       | close |
      | AAPL   | 2024-01-01 | 100   |
      | AAPL   | 2024-01-02 | 110   |
      | AAPL   | 2024-01-03 | 110   |
      | AAPL   | 2024-01-04 | 132   |
      | AAPL   | 2024-01-05 | 145.2 |
    When I execute "mrmkt indicators volatility-percentile AAPL --period 2 --lookback 2 --from 2024-01-05 --to 2024-01-05"
    Then the command succeeds
    And the indicator output has column "VOL_2D_PCTL_2D" and these values:
      | date       | close | value |
      | 2024-01-05 | 145.2 | 0     |

  Scenario: Calculate a separate rolling percentile of volatility of volatility
    Given the local price catalog contains these daily bars:
      | symbol | date       | close  |
      | AAPL   | 2024-01-01 | 100    |
      | AAPL   | 2024-01-02 | 110    |
      | AAPL   | 2024-01-03 | 110    |
      | AAPL   | 2024-01-04 | 132    |
      | AAPL   | 2024-01-05 | 145.2  |
      | AAPL   | 2024-01-06 | 188.76 |
      | AAPL   | 2024-01-07 | 188.76 |
    When I execute "mrmkt indicators vol-of-vol-percentile AAPL --vol-period 2 --vov-period 2 --lookback 2 --from 2024-01-07 --to 2024-01-07"
    Then the command succeeds
    And the indicator output has column "VOV_2D_2D_PCTL_2D" and these values:
      | date       | close  | value |
      | 2024-01-07 | 188.76 | 0     |

  Scenario: A relative start date defaults to the fake clock's current date
    Given the fake clock says today is "2024-01-31"
    And the local price catalog contains these daily bars:
      | symbol | date       | close |
      | AAPL   | 2024-01-20 | 100   |
      | AAPL   | 2024-01-24 | 102   |
      | AAPL   | 2024-01-31 | 104   |
    When I execute "mrmkt indicators sma AAPL --period 1 --from 7d"
    Then the command succeeds
    And the indicator output has column "SMA_1D" and these values:
      | date       | close | value |
      | 2024-01-24 | 102   | 102   |
      | 2024-01-31 | 104   | 104   |

  Scenario: Calculate a volatility-implied risk range with buy and sell levels
    Given the local price catalog contains these daily bars:
      | symbol | date       | close |
      | AAPL   | 2024-01-01 | 100   |
      | AAPL   | 2024-01-02 | 110   |
      | AAPL   | 2024-01-03 | 100   |
      | AAPL   | 2024-01-04 | 110   |
    When I execute "mrmkt indicators risk-range AAPL --horizon 1 --vol-period 2 --width 1.0 --anchor-period 2 --from 2024-01-03 --to 2024-01-04"
    Then the command succeeds
    And the indicator output has columns "RR_1D_LRR" and "RR_1D_TRR" and these values:
      | date       | close | low     | high    |
      | 2024-01-03 | 100   | 90.8472 | 119.153 |
      | 2024-01-04 | 110   | 90.8472 | 119.153 |
