Feature: Agent Registry

  Scenario: Register agent
    Given the agent registry is empty
    When I register the agent "taxi_agent" with capability "taxi-search"
    Then the agent "taxi_agent" is registered

  Scenario: Retrieve agent
    Given an agent "taxi_agent" is registered
    When I retrieve the agent "taxi_agent"
    Then the response contains the agent "taxi_agent"

  Scenario: Disable agent
    Given an agent "taxi_agent" is registered
    When I disable the agent "taxi_agent"
    Then the agent "taxi_agent" is disabled

  Scenario: Enable agent
    Given the agent "taxi_agent" is registered and disabled
    When I enable the agent "taxi_agent"
    Then the agent "taxi_agent" is enabled

  Scenario: Delete agent
    Given an agent "taxi_agent" is registered
    When I delete the agent "taxi_agent"
    Then the agent "taxi_agent" is no longer registered

  Scenario: Reject duplicate agent
    Given an agent "taxi_agent" is registered
    When I register the agent "taxi_agent" again
    Then the duplicate registration is rejected with status 409