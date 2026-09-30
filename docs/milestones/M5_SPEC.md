---
document: M5_SPEC
status: DRAFT
milestone: M5
authority: SOURCE_OF_TRUTH
---
# MILESTONE 5: MEMORY GOVERNANCE & AUTHORIZATION

## 1. Purpose
Establish authorization and governance for persistent memory operations (READ, WRITE, DELETE).

## 2. Core Principles
- `READ ≠ WRITE ≠ DELETE`
- Validation before Authorization.
- Fail-closed behavior.
- M4 security invariants are immutable.

## 3. Requirements
- **Operation Identity:** Every invocation has a runtime-generated internal ID.
- **Argument Validation:** Strict schema validation before authorization.
- **Authorization Model:** Distinguish READ/WRITE/DELETE based onTrusted Classification.
- **Approval Binding:** Grants bound to `(namespace, memory_id)` and operation.
- **Replay Protection:** Atomic single-use grants.
- **Delete Protection:** DELETE always requires independent authorization.
- **Provider Boundary:** Providers perform persistence only, not authorization.

## 4. Definition of Done
- All security invariants (INV-01 to INV-14) verified.
- M4 regression tests pass.
- M5 security test suite passes.
- Independent audit complete.
- Merged to `main`.
