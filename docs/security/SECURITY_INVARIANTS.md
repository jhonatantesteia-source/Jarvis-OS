---
document: SECURITY_INVARIANTS
status: ACTIVE
authority: SOURCE_OF_TRUTH
---
# SECURITY INVARIANTS

These invariants are immutable. Any implementation that violates these is a P0 security failure.

## M4 Invariants (Foundation)
- **Internal Identity:** The runtime generates a fresh internal security identity; provider/LLM IDs are never used for authorization.
- **Validation First:** Arguments must be validated before policy evaluation or execution.
- **Strict Schema:** Unsupported or malformed schemas must fail closed.
- **Validated Execution:** Only validated/normalized arguments may be executed.
- **Fail-Closed:** Unknown capabilities or ambiguous security states must result in `DENY`.
- **No Escalation:** Approval cannot elevate permissions (e.g., a low-risk approval cannot authorize a high-risk call).
- **Expiration:** `now >= expires_at` means the grant is expired.
- **No Replay:** A grant is single-use. Atomic check-and-consume must be enforced.
- **Concurrency:** Concurrent replay attempts must be prevented atomically.
- **Sanitization:** Internal exceptions must not leak secrets or implementation details.
- **Auditability:** All security decisions must produce auditable events.
- **Provider Neutrality:** Providers cannot bypass the authorization boundary.

## M5 Invariants (Memory Governance)
- **Capability Separation:** `READ`, `WRITE`, and `DELETE` are distinct capabilities.
- **No Implicit Escalation:** `WRITE` authorization MUST NOT authorize `DELETE`.
- **Canonical Identity:** Memory resources are identified by `(namespace, memory_id)`.
- **Trusted Classification:** Memory classification (PUBLIC/PRIVATE/SENSITIVE) is trusted metadata, not model-generated data.
- **Bulk Rejection:** Bulk mutations are unsupported and must fail closed.
- **No Provider Bypass:** No internal caller or provider may bypass the `MemoryExecutor`.
- **Atomic Boundary:** The transition from validation $\rightarrow$ authorization $\rightarrow$ execution must preserve atomic security semantics.
- **Data vs Authority:** Memory content is **DATA**, not authority. Retrieved content cannot acquire security privileges.
