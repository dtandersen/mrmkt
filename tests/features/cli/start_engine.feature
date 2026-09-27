Feature: Start engine CLI
  As a MrMkt operator
  I want mrmkt engine start to start the engine
  So that the engine attaches without a direct exchange connection

  Scenario: Engine start subscribes to the subject
    When I execute "mrmkt engine start"
    Then the command succeeds
    And the queue is subscribed to "subscribe.realtime.price"
