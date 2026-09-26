Feature: Trigger JSON API
  As a remote operator
  I want trigger CRUD over HTTP DTOs
  So that the CLI can manage cluster-side triggers without Postgres

  Scenario: Listing an empty catalog returns an empty array
    Given the JSON API is running
    When I list triggers via the API
    Then the API response status is 200
    And the API list is empty

  Scenario: Creating a trigger returns its DTO with an id
    Given the JSON API is running
    When I create a trigger via the API with:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
      | frequency | once          |
    Then the API response status is 201
    And the API response contains:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
      | frequency | once          |
      | enabled   | true          |
    When I list triggers via the API
    Then the API list contains trigger "dip-watch"

  Scenario: Creating a trigger with a bad operator is rejected
    Given the JSON API is running
    When I create a trigger via the API with:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | sideways      |
    Then the API response status is 400
    And the API response errors mention "invalid operator"

  Scenario: Creating a duplicate trigger is rejected
    Given the JSON API is running
    When I create a trigger via the API with:
      | field     | value         |
      | name      | first         |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
    Then the API response status is 201
    When I create a trigger via the API with:
      | field     | value         |
      | name      | second        |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
    Then the API response status is 400
    And the API response errors mention "already exists"

  Scenario: Deleting an unknown trigger returns 404
    Given the JSON API is running
    When I delete trigger id 999 via the API
    Then the API response status is 404
    And the API response errors mention "no trigger with id 999"

  Scenario: Deleting a trigger removes it from the list
    Given the JSON API is running
    When I create a trigger via the API with:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
    Then the API response status is 201
    When I delete the created trigger via the API
    Then the API response status is 200
    And the API response contains:
      | field | value     |
      | name  | dip-watch |
    When I list triggers via the API
    Then the API list is empty

  Scenario: Enabled-only listing hides disabled triggers
    Given the JSON API is running
    When I create a trigger via the API with:
      | field     | value         |
      | name      | dip-watch     |
      | symbol    | AAA           |
      | indicator | risk-range    |
      | operator  | crossing-down |
    Then the API response status is 201
    When I disable the created trigger via the API
    Then the API response status is 200
    And the API response contains:
      | field   | value |
      | enabled | false |
    When I list enabled triggers via the API
    Then the API list is empty
    When I list triggers via the API
    Then the API list contains trigger "dip-watch"

  Scenario: Toggling an unknown trigger returns 404
    Given the JSON API is running
    When I set trigger id 999 enabled via the API
    Then the API response status is 404
    And the API response errors mention "no trigger with id 999"
