Feature: MCP Registry

  Scenario: Register MCP server
    Given the MCP registry is empty
    When I register the MCP server "taxi-tools" with endpoint "stdio://taxi-tools"
    Then the server "taxi-tools" is registered
    And the registry contains 1 servers

  Scenario: Retrieve registered MCP server
    Given an MCP server "taxi-tools" is registered
    When I retrieve the MCP server "taxi-tools"
    Then the response contains the server "taxi-tools"

  Scenario: Disable MCP server
    Given an MCP server "taxi-tools" is registered
    When I disable the MCP server "taxi-tools"
    Then the server "taxi-tools" is disabled

  Scenario: Enable MCP server
    Given the MCP server "taxi-tools" is registered and disabled
    When I enable the MCP server "taxi-tools"
    Then the server "taxi-tools" is enabled

  Scenario: Delete MCP server
    Given an MCP server "taxi-tools" is registered
    When I delete the MCP server "taxi-tools"
    Then the server "taxi-tools" is no longer registered

  Scenario: Reject duplicate MCP server
    Given an MCP server "taxi-tools" is registered
    When I register the MCP server "taxi-tools" again
    Then the duplicate registration is rejected with status 409

  Scenario: Do not return disabled server as active
    Given an MCP server "taxi-tools" is registered
    And the MCP server "car-tools" is registered and disabled
    When I list enabled MCP servers
    Then only the server "taxi-tools" is returned