Feature: Critic refinement

  Scenario: Critic identifies a constraint violation
    Given the planner produced a proposal violating a three-day constraint
    When the critic reviews the proposal
    Then the critic produces a specific question
    And the refiner produces a revised proposal

  Scenario: Unresolved proposal terminates safely
    Given the critic keeps finding an unresolved issue
    When the refinement loop reaches three iterations
    Then the workflow abstains and requests human review
