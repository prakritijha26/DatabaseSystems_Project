# 0002 — Review 2 transactional demonstration boundary

**Date:** 2026-10-15
**Status:** Accepted

## Context
The milestone needs real DML, narrowly scoped DDL and catalog evidence. Existing identity sequences advance outside rollback. Missing attendance rows previously disappeared from eligibility results. A weighted score alone is not GPA.

## Decision
Use explicit integer primary keys for course, enrollment, attendance and mark inserts; use UUID audit IDs so the trusted schema has no sequence side effects. Keep missing attendance as a zero-percent, ineligible result for an existing enrollment. Add a clearly labeled demonstration GPA from score bands (90/80/70/60/50/40 map to 10/9/8/7/6/5; below 40 maps to 0), weighted by course credits. This is not an official VIT grading policy.

Allow only a bounded SQL AST subset on public university relations. Reject function calls outside the approved read-only set, modifying CTEs, SELECT INTO, locks, cross-schema references and transaction commands. Inspect catalog dependencies before ALTER TABLE DROP COLUMN; first attempt normal RESTRICT semantics in a savepoint, then explicitly report a CASCADE preview if dependencies block it, and roll back the entire transaction. Verification SELECT is read-only and cannot alone prove prior immutability; the scenario tests compare complete row and catalog fingerprints.

## Consequences
A fresh Review 2 database is needed; never silently migrate an existing data volume. Database contents and modeled schema changes roll back, but PostgreSQL may write WAL, take locks and do physical I/O. Catalog dependencies cannot fully detect references embedded in dynamic SQL/function bodies. Use the trusted project schema for this demonstration, not arbitrary production schemas.

## Alternatives
1. Accept sequence gaps and promise row-only immutability: simpler, but leaves an observable persistent state change after INSERT and mark-update audit triggers.
2. Clone a database for every simulation: stronger isolation from custom external effects, but higher latency and operational complexity for this milestone.
3. Execute only RESTRICT DDL: safe and faithful, but shows an error rather than the hypothetical cascade closure; the chosen path labels the expanded CASCADE preview explicitly.

## Payoff trigger
Before production use, replace demonstration grade bands with approved policy, add restricted roles and workload isolation, and validate external-effect functions/triggers and concurrent clients.
