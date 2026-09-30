---
document: MILESTONES
status: ACTIVE
authority: SOURCE_OF_TRUTH
---
# MILESTONES INDEX

## M1 — Garmin Device Recognition
- **Purpose:** Detect Garmin watches via USB mass storage.
- **Status:** CLOSED
- **Specification:** [DOCUMENTATION GAP] (Implemented in `integrations/garmin/`)

## M2 — Agent Loop & Tool Foundation
- **Purpose:** Basic agent-tool loop and provider factory.
- **Status:** CLOSED
- **Specification:** [DOCUMENTATION GAP]

## M3 — Persistent Memory
- **Purpose:** Introduction of MemoryProvider abstraction.
- **Status:** CLOSED
- **Specification:** [DOCUMENTATION GAP]

## M4 — HITL Security Hardening
- **Purpose:** Secure the tool invocation boundary with strict validation and HITL.
- **Status:** CLOSED
- **Merge Commit:** `19a660e5eceaaa3f5be7fa2377aa130feb5efc72`
- **Specification:** `docs/milestones/M4_SPEC.md`
- **Threat Model:** `docs/security/threat-models/M4_THREAT_MODEL.md`
- **ADRs:** `docs/security/adr/M4_ADR.md`
- **Test Plan:** `docs/testing/M4_SECURITY_TEST_PLAN.md`

## M5 — Memory Governance & Authorization
- **Purpose:** Establish authorization for persistent memory operations.
- **Status:** IN PROGRESS
- **Specification:** `docs/milestones/M5_SPEC.md`
- **Threat Model:** `docs/security/threat-models/M5_THREAT_MODEL.md`
- **ADRs:** `docs/security/adr/M5_ADR.md`
- **Test Plan:** `docs/testing/M5_SECURITY_TEST_PLAN.md`
- **Constraints:** M4 invariants are immutable.
