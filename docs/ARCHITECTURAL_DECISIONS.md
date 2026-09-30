---
document: ARCHITECTURAL_DECISIONS
status: ACTIVE
authority: SOURCE_OF_TRUTH
---
# ARCHITECTURAL DECISIONS INDEX

## M5 — Memory Governance

| ID | Title | Status | Decision | Rationale |
|----|-------|--------|----------|-----------|
| ADR-01 | Resource Identity | ACCEPTED | `(namespace, memory_id)` | Ensures canonical resource binding across providers. |
| ADR-02 | Memory Classification | ACCEPTED | PUBLIC / PRIVATE / SENSITIVE | Trusted metadata for differentiated policy. |
| ADR-03 | READ Approval | ACCEPTED | PUBLIC/PRIVATE $\rightarrow$ ALLOW, SENSITIVE $\rightarrow$ HITL | Balances utility with sensitivity. |
| ADR-04 | WRITE Approval | ACCEPTED | PUBLIC/PRIVATE $\rightarrow$ ALLOW, SENSITIVE $\rightarrow$ HITL | Prevents unauthorized sensitive state mutation. |
| ADR-05 | DELETE Policy | ACCEPTED | Always `REQUIRE_USER_APPROVAL` | Highest risk operation requires explicit consent. |
| ADR-06 | Bulk Operations | ACCEPTED | Unsupported in M5 $\rightarrow$ DENY | Prevents mass deletion/mutation vulnerabilities. |
| ADR-07 | TOCTOU / Atomicity | ACCEPTED | Atomic validation $\rightarrow$ execution boundary | Prevents stale authorization. |
| ADR-08 | Internal Access | ACCEPTED | No direct provider bypass | Maintains single point of enforcement. |
| ADR-09 | Policy Architecture | ACCEPTED | Reuse M4 authorization primitives | Minimizes duplicated security logic. |
