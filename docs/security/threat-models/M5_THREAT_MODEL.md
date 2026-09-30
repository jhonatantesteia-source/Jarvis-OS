---
document: M5_THREAT_MODEL
status: ACCEPTED
milestone: M5
authority: SOURCE_OF_TRUTH
---
# M5 THREAT MODEL

## 1. Security Objective
No component may read, write, or delete persistent memory unless the specific operation has passed the appropriate validation and authorization boundary.

## 2. Key Threats (Summary)
- **T-01 to T-11:** Identity spoofing, operation confusion, argument substitution, and approval replay.
- **T-12 to T-16:** Provider bypass, provider escalation, and resource identity confusion.
- **T-17 to T-20:** TOCTOU, audit leakage, and unauthorized READ.
- **T-21 to T-24:** Malicious memory injection and prompt injection (Memory content $\neq$ Authority).
- **T-25 to T-34:** Exception disclosure, DoS, internal bypass, and state desynchronization.

## 3. Mandatory Invariants
- **INV-01:** No Unvalidated Execution.
- **INV-02:** No Provider-Controlled Security Identity.
- **INV-03:** Capability Separation (READ $\neq$ WRITE $\neq$ DELETE).
- **INV-04:** Exact Approval Binding.
- **INV-05:** No Authorization Escalation.
- **INV-06/07:** Provider cannot authorize or escalate.
- **INV-08:** Fail Closed.
- **INV-09/10:** Approval is single-use and atomic.
- **INV-11:** Memory is Untrusted Data.
- **INV-12:** Audit Minimization.
- **INV-13:** Destructive Operations Require Explicit Semantics.
- **INV-14:** M4 Invariants are Immutable.
