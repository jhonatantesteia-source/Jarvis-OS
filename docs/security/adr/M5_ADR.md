---
document: M5_ADR
status: ACCEPTED
milestone: M5
authority: SOURCE_OF_TRUTH
---
# M5 ARCHITECTURAL DECISIONS

## ADR-01: Resource Identity
**Decision:** Canonical identity is `(namespace, memory_id)`.

## ADR-02: Memory Classification
**Decision:** Three-tier: PUBLIC, PRIVATE, SENSITIVE. Trusted metadata.

## ADR-03: READ Approval
**Decision:** PUBLIC/PRIVATE $\rightarrow$ ALLOW; SENSITIVE $\rightarrow$ REQUIRE_USER_APPROVAL.

## ADR-04: WRITE Approval
**Decision:** PUBLIC/PRIVATE $\rightarrow$ ALLOW; SENSITIVE $\rightarrow$ REQUIRE_USER_APPROVAL.

## ADR-05: DELETE Policy
**Decision:** Always `REQUIRE_USER_APPROVAL`.

## ADR-06: Bulk Operations
**Decision:** Unsupported in M5 $\rightarrow$ DENY.

## ADR-07: TOCTOU / Atomicity
**Decision:** Atomic validation $\rightarrow$ authorization $\rightarrow$ execution boundary.

## ADR-08: Internal Access
**Decision:** No direct provider bypass.

## ADR-09: Policy Architecture
**Decision:** Reuse M4 authorization primitives; avoid parallel security universe.
