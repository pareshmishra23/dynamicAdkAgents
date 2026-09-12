# Dynamic Agent Platform Interview Guide

## 1. Why use an Agent Registry?

The registry makes reusable agents discoverable and gives the runtime one authority for identity, version, enabled state, capabilities, and permissions. The router does not need hard-coded knowledge of every specialist.

## 2. Why dynamically select agents?

A request may need different capabilities. Dynamic selection avoids creating a separate workflow for every combination and ensures that only relevant agents are exposed for a request.

## 3. Agent versus Agent-as-a-Tool

An agent is an autonomous reasoning specialist. Agent-as-a-Tool is an adapter that exposes a selected agent through a constrained callable interface so another agent can delegate a specific task and receive a structured result.

## 4. Router versus Orchestrator

The router answers **who is required?** The orchestrator answers **how should they be executed and integrated?** Keeping these responsibilities separate prevents the router from silently executing work and preserves one final decision owner.

## 5. Sequential versus Parallel execution

Independent tasks such as sightseeing and taxi planning can run in parallel. Dependent steps such as integration, budget validation, and final writing should run sequentially.

## 6. LoopAgent, Critic, and Refiner

The critic challenges a proposal and must identify a concrete issue when one exists. The refiner revises the proposal. A hard maximum of three iterations prevents infinite loops; unresolved cases abstain and request human review.

## 7. MCP versus Agent-as-a-Tool

MCP is an integration protocol or boundary for deterministic external capabilities. Agent-as-a-Tool delegates reasoning to another agent. A specialist may use MCP-backed tools, but not every specialist should depend on MCP.

## 8. Tool Registry versus Agent Registry

The agent registry describes reasoning specialists. The tool registry describes callable capabilities. Separating them supports least privilege and makes deterministic actions easier to audit.

## 9. Configuration-driven agents

YAML configuration keeps instructions, capabilities, versions, limits, and allowed tools out of a large Python file. The loader validates configuration before runtime use.

## 10. Runtime policy

Runtime policy controls timeouts, maximum tool calls, concurrency, retries, and error handling. These are operational safeguards, not suggestions to the model.

## 11. Least privilege

Each agent receives only the tools declared in its configuration. The initial design does not allow an LLM to execute arbitrary Python, SQL, filesystem operations, or agent names.

## 12. Agent versioning

Version metadata makes behavior traceable and allows an updated definition to be tested and rolled back without losing the previous known-good version.

## 13. Failure handling

Unknown, disabled, malformed, timed-out, or failed agents are rejected or reported in a controlled way. Retries must be bounded, and unavailable external integrations must not become infinite loops.

## 14. Observability

Every request should have a request/session ID. Logs should capture selected agent IDs, versions, workflow stage, iteration, success/failure, and duration, while never logging API keys or complete sensitive user data.

## 15. Single decision-owner principle

> Agents are reusable reasoning specialists. The registry makes them discoverable. The router determines which capabilities are required for a particular request. Selected agents are dynamically exposed through an Agent-as-a-Tool interface to the orchestrator. The orchestrator composes those capabilities using sequential, parallel and bounded iterative workflows while maintaining a single clearly defined final decision owner.

## 16. Why deterministic state mutation should not be owned directly by LLM reasoning

LLMs are useful for interpretation, planning, and analysis, but deterministic mutations should be mediated by typed tools with validation, authorization, and audit logging. This makes side effects reviewable and prevents generated text from becoming unrestricted executable authority.
