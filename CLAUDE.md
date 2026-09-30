# CLAUDE.md

This is the Claude operating manual for the Jarvis OS repository.

## Project Identity
Jarvis OS is a modular personal AI operating system developed through Specification-Driven Development. Claude acts as the implementation engineer.

Architecture, security, milestone scope, and authorization boundaries are governed by the project's authoritative documentation in the `docs/` directory.

## Mandatory Boot Sequence
At the beginning of every development session, Claude MUST:
1. Read `CLAUDE.md`.
2. Read `docs/JARVIS_CONSTITUTION.md`.
3. Read `docs/PROJECT_STATE.md`.
4. Read `docs/PROJECT_SPEC.md`.
5. Read `docs/MILESTONES.md`.
6. Identify the active milestone.
7. Read the active milestone specification.
8. Read applicable security invariants in `docs/security/SECURITY_INVARIANTS.md`.
9. Read applicable threat models in `docs/security/threat-models/`.
10. Read applicable ADRs in `docs/security/adr/`.
11. Read applicable security test plans in `docs/testing/`.
12. Inspect the current implementation before modifying it.

Claude must never assume that conversational context is sufficient.

## Specification Discipline
- **Conflict:** If specification and implementation disagree: STOP → REPORT → DO NOT SILENTLY REINTERPRET.
- **Ambiguity:** If a requirement is ambiguous: STOP → IDENTIFY AMBIGUITY → REQUEST ARCHITECTURAL DECISION.

## Change Discipline
- No unrelated refactoring.
- No silent architecture changes.
- No speculative features.
- No implementation of future milestones.
- No weakening of security tests.
- No removal of security controls for convenience.
