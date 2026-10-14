# 0001 — Normalize live reports at the application boundary

**Date:** 2026-10-14
**Status:** Accepted

## Context
The delivered DML engine returns table counts and rollback state. Clients consume ImpactReport. The delivered schema uses enrollment IDs and weighted scores; offline fixtures use a different academic model, CGPA, and DDL examples.

## Decision
Normalize raw reports in app.py and route HTTP and CLI clients through that shared entry point. Fall back to explicitly labeled offline fixtures only when runtime dependencies or a database connection are unavailable. Validation and SQL execution errors remain errors. Preserve raw engine access for callers needing counts. Start REPEATABLE READ before baseline capture and always roll back in finally.

## Consequences
Clients receive one contract without changing the delivered schema. Mock reports are visibly demonstrations, never live rollback evidence. Live weighted scores are not labeled CGPA. Unsupported live DDL and verification SELECT remain explicit errors. Transaction rollback does not promise zero physical disk writes or reversal of sequence increments.

## Alternatives
1. Rewrite the engine to emit ImpactReport directly: removes the adapter but couples the engine to presentation and changes its existing raw-report API.
2. Adapt separately in each client: preserves the engine but duplicates fallback, error, and metric mapping rules.

## Payoff trigger
Revisit when the live engine supports catalog tracing and the agreed academic metrics. Consolidate schemas and retire divergent fixtures then.
