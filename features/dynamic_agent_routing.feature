Feature: Dynamic agent selection

  Scenario: New York multi-capability trip
    Given the agent registry contains the five travel specialist agents
    When the user requests sightseeing, adventure, car rental, taxi and social visits
    Then the router selects the required specialist agents
    And the orchestrator receives only those selected agents

  Scenario: Unknown agent protection
    Given the agent registry does not contain "banking_magic_agent"
    When the router selects "banking_magic_agent"
    Then the routing request is rejected
    And the unknown agent is not executed
