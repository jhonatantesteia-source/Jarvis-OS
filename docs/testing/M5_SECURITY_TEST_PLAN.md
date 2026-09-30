---
document: M5_SECURITY_TEST_PLAN
status: AWAITING_APPROVAL
milestone: M5
authority: SOURCE_OF_TRUTH
---
# M5 SECURITY TEST PLAN

## Status: AWAITING APPROVAL
This document defines the mandatory security tests for Milestone 5.

## 1. Mandatory Test Families
- **Identity:** Provider ID manipulation, missing internal ID.
- **Capability:** READ $\neq$ WRITE $\neq$ DELETE separation.
- **Resource Binding:** Wrong `(namespace, memory_id)` usage.
- **Approval:** Replay, expiration, argument/operation mismatch.
- **Validation:** Malformed/unsupported schemas, unknown arguments.
- **Provider Boundary:** Direct access attempts, provider escalation.
- **Prompt Injection:** Memory content attempting to acquire authority.
- **Audit:** Event emission and data minimization.
- **Regression:** All M4 security tests must pass.

## 2. P0 Security Gates
- **P0-1:** READ cannot escalate to WRITE or DELETE.
- **P0-2:** WRITE cannot escalate to DELETE.
- **P0-3:** Approval for one resource cannot authorize another.
- **P0-4:** Single-use approvals cannot be consumed concurrently.
- **P0-5:** Empty/Invalid schemas fail closed.
- **P0-6:** Memory content cannot trigger privileged tool calls.
- **P0-7:** Direct provider access is blocked.
