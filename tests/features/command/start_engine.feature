Feature: Start engine
  As a MrMkt operator
  I want the engine to consume realtime price events from the message queue
  So that trigger hits print without a direct exchange connection

  Scenario: Engine subscribes to subscription events when it starts
    When the engine starts
    Then the engine is subscribed to "subscribe.realtime.price" events

  Scenario: Engine streams enabled stored triggers on start
    Given stored trigger "dip-watch" for "AAA"
    When the engine starts
    Then the engine starts streaming stock price data for AAA on a new thread

  Scenario: Engine subscribes to market price events when it gets a subscription
    Given the engine is started
    And the price data:
    When the message "subscribe.realtime.price" for "AAPL" is sent
    Then the engine starts streaming stock price data for AAPL on a new thread
    When the price provider pushes:
      | symbol | timestamp | bid | ask |
      | AAPL   | ?         | 100 | 101 |
    Then the price data is sent to the "subscribe.realtime.price.AAPL" channel:
      | symbol | timestamp | bid | ask |
      | AAPL   | ?         | 100 | 101 |
    When the price provider pushes:
      | symbol | timestamp | bid | ask |
      | AAPL   | ?         | 102 | 103 |
    Then the price data is sent to the "subscribe.realtime.price.AAPL" channel:
      | symbol | timestamp | bid | ask |
      | AAPL   | ?         | 100 | 101 |
      | AAPL   | ?         | 102 | 103 |
