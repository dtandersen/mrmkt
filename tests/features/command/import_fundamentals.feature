Feature: Import as-reported fundamentals from Tiingo
  As a MrMkt operator
  I want quarterly filings plus daily market caps in the local store
  So that income-first fundamental analysis reads from local data

  Scenario: Imported statements and enterprise value land in the store
    Given a clean fundamentals store
    And stored bars:
      | symbol | date       | close |
      | AAA    | 2024-03-31 | 40    |
      | AAA    | 2024-04-01 | 50    |
    And a fake fundamentals source serving "AAA" with filing "2024-03-31" and caps "2024-04-01:50000,2024-04-02:60000"
    When I import "AAA" fundamentals
    Then 1 income statements are stored for "AAA"
    And 1 balance sheets are stored for "AAA"
    And 1 cash flows are stored for "AAA"
    And 2 enterprise values are stored for "AAA"
    And 5 fundamentals rows were imported
    And the enterprise value for "AAA" on "2024-04-01" uses price 50 with 1000 shares and cap 50000
    And the enterprise value for "AAA" on "2024-04-02" uses price 50 with 1000 shares and cap 60000

  Scenario: A failing batch is recorded, not fatal
    Given a clean fundamentals store
    And a fake fundamentals source failing batch "AAA,BBB"
    When I import "AAA,BBB" fundamentals
    Then the batch "AAA,BBB" is recorded failed
    And 0 income statements are stored for "AAA"

  Scenario: Transient failures are retried with backoff then succeed
    Given a clean fundamentals store
    And stored bars:
      | symbol | date       | close |
      | AAA    | 2024-03-31 | 40    |
    And a fake fundamentals source serving "AAA" with filing "2024-03-31" and caps "2024-04-01:50000"
    And batch "AAA" fails 2 times before succeeding
    When I import "AAA" fundamentals
    Then 1 income statements are stored for "AAA"
    And the fundamentals source was called 3 times
    And the retry delays were:
      | seconds |
      | 1.0     |
      | 2.0     |
    And progress reports were:
      | done | total |
      | 1    | 1     |

  Scenario: Daily points without prior filings or bars store no enterprise value
    Given a clean fundamentals store
    And a fake fundamentals source serving "BBB" with filing "2024-03-31" and caps "2024-03-01:10000"
    When I import "BBB" fundamentals
    Then 1 income statements are stored for "BBB"
    And 0 enterprise values are stored for "BBB"
    And 3 fundamentals rows were imported

  Scenario: Re-importing stored fundamentals counts nothing new
    Given a clean fundamentals store
    And stored bars:
      | symbol | date       | close |
      | AAA    | 2024-03-31 | 40    |
    And a fake fundamentals source serving "AAA" with filing "2024-03-31" and caps "2024-04-01:50000"
    When I import "AAA" fundamentals
    Then 4 fundamentals rows were imported
    When I import "AAA" fundamentals again
    Then 0 fundamentals rows were imported

  Scenario: A persistently failing batch is isolated with per-batch progress
    Given a clean fundamentals store
    And a fake fundamentals source serving "AAA" with filing "2024-03-31" and caps "2024-04-01:50000"
    And a fake fundamentals source serving "BBB" with filing "2024-03-31" and caps "2024-04-01:60000"
    And a fake fundamentals source failing batch "AAA"
    And the import batch size is 1
    When I import "AAA,BBB" fundamentals
    Then the batch "AAA" is recorded failed
    And 0 income statements are stored for "AAA"
    And 1 income statements are stored for "BBB"
    And progress reports were:
      | done | total |
      | 1    | 2     |
      | 2    | 2     |
