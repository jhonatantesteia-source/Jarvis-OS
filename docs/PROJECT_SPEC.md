---
document: PROJECT_SPEC
status: ACTIVE
authority: SOURCE_OF_TRUTH
---
# PROJECT SPECIFICATION

## 1. Project Purpose
Jarvis OS is a modular personal AI operating system designed to provide a secure, agentic interface to local and remote resources.

## 2. Architectural Philosophy
- **Specification-Driven:** All features are defined in specs before implementation.
- **Security-First:** Security boundaries are explicit and enforced via a trusted runtime.
- **Provider Agnostic:** Core logic is decoupled from specific LLM or Memory providers.

## 3. Core Modules
- **Agent Runtime:** Orchestrates the loop between LLM and Tool/Memory execution.
- **ToolInvocationBoundary:** Validates and authorizes tool calls before execution.
- **PolicyEngine:** Determines authorization decisions based on risk levels.
- **ApprovalProvider:** Manages Human-in-the-Loop (HITL) authorization.
- **MemoryProvider:** Handles persistent storage of state.
- **SecurityAuditLogger:** Records security-relevant events.

## 4. Security Model
- **Boundary Enforcement:** Strict validation $\rightarrow$ Policy $\rightarrow$ Approval $\rightarrow$ Execution.
- **Identity:** Runtime-generated internal IDs are the sole security identity.
- **Fail-Closed:** Any failure in the security chain results in a `DENY`.

## 5. Memory Model
- **Abstraction:** Decoupled providers for different storage backends.
- **Governance (M5):** Explicit capabilities for READ, WRITE, and DELETE.

## 6. Development Methodology
- Sequential milestones.
- Mandatory security audits.
- Git-based versioning of specs and ADRs.
