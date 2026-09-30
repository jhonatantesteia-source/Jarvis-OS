---
document: JARVIS_CONSTITUTION
status: ACTIVE
authority: SOURCE_OF_TRUTH
---
# JARVIS CONSTITUTION

## 1. Architecture Principles
- **Modular Architecture:** Explicit component boundaries and separation of concerns.
- **Specification-Driven Development:** Implementation follows approved specifications.
- **Governance:** Architecture is changed through explicit architectural decisions (ADRs), not accidental drift.

## 2. Security Principles
- **Least Privilege:** Components have only the minimum authority needed.
- **Fail-Closed Behavior:** Any uncertainty, error, or ambiguity in security state results in denial/rejection.
- **Explicit Authorization:** No implicit privilege escalation.
- **Validation Before Execution:** All inputs must be validated before policy evaluation or execution.
- **Provider Neutrality:** Security boundaries must not be bypassed by providers; providers must not perform authorization.
- **Auditability:** All security-critical decisions must be recorded.

## 3. Authority Model
- **DATA vs INSTRUCTIONS vs AUTHORITY:**
    - Memory content is **DATA**, not authority.
    - Model-generated content must never independently acquire security authority.
    - Authorization must originate from the trusted runtime/policy layer.

## 4. Human Control
- Human authorization (HITL) is authoritative for operations requiring approval.

## 5. Milestone Governance
- Milestones are sequential.
- A milestone is only closed when it satisfies its specific "Definition of Done" and passes an independent security audit.
