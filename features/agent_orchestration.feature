Feature: Agent orchestration

  Scenario: Independent specialist work runs in parallel
    Given the router selected sightseeing, adventure and taxi agents
    When the orchestrator executes the request in parallel
    Then each selected agent is exposed as an agent-as-a-tool
    And the orchestrator integrates all specialist results

  Scenario: Dependent work runs sequentially
    Given specialist results are available
    When the orchestrator runs sequential integration
    Then the final decision owner is the orchestrator
