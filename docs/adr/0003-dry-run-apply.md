# 0003 — Explicit dry-run, apply, and sample recovery

**Date:** 2026-10-21
**Status:** Accepted for the local course demonstration

## Context

The console needs an explicit permanent execution command alongside its existing snapshot simulation. The same AST whitelist must protect both modes. The current DDL simulation can expand a dependency-blocked RESTRICT operation into a rolled-back CASCADE preview; silently committing that expansion would change the user's requested operation. The seed file only inserts data, so replaying it alone cannot recover a dropped column or table.

## Decision

Use WHAT_IF and APPLY prefixes with the same single-statement AST validation and REPEATABLE READ transaction setup. WHAT_IF captures results and rolls back. APPLY commits only after execution and supported telemetry collection succeed, and reports permanent success only after PostgreSQL acknowledges commit. Errors attempt rollback and never produce a successful commit report. Read-only SELECT continues to roll back.

APPLY DDL retains RESTRICT semantics. A dependency failure rejects the permanent operation; only WHAT_IF may expand it to the explicitly labeled CASCADE preview. DDL does not fabricate academic metrics when its schema changes make those queries unavailable.

RESEED and RESET rebuild the named sample tables, views, and audit function transactionally using schema.sql followed by seed.sql, then commit. Recovery is a destructive reset of the dedicated demonstration schema, including dependent objects removed through CASCADE. It is not a general migration or backup restore facility and must not target a shared production schema.

HTTP execution requires JSON and rejects a supplied cross-origin Origin header. The CLI does not automatically replay a permanent command after an ambiguous HTTP failure: the original transaction might already have committed. Users must inspect data before retrying. A connection refusal before dispatch may use the local adapter.

Offline COMMITTED acknowledgements describe a mock fixture only. They do not persist SQL changes, establish read-back evidence, or justify PostgreSQL commit confirmation. The adapter and both interfaces must keep the backend scope visible.

This is a two-step human workflow with separate transactions. It does not use PostgreSQL prepared transactions or distributed two-phase commit, and the APPLY snapshot may differ from an earlier WHAT_IF snapshot.

## Consequences

The demonstration can compare rollback and commit with one validation policy and recover its sample schema after destructive changes. The audit trigger participates in the same transaction. Commit acknowledgement does not establish physical zero-write guarantees for simulations. Concurrent changes can invalidate an earlier preview, and ambiguous commit outcomes require explicit read-back. The trusted local schema, existing connection credentials, and lack of user authorization remain unsuitable for deployment beyond the course environment.

## Alternatives

1. Bind APPLY to a stored preview token and schema/data version, rejecting stale previews. This provides stronger review-to-write consistency but requires durable preview state and concurrency policy beyond the present demonstration.
2. Use prepared transactions and a separate commit command. This retains transaction resources while awaiting a decision, requires recovery of abandoned transactions, and adds operational complexity without a distributed participant requirement.
3. Restore only row data by truncating and replaying seed.sql. This is smaller but cannot repair DDL damage, so transactional schema reconstruction is selected.

## Payoff trigger

Before deployment outside a dedicated local demonstration database, or when concurrent review-to-apply consistency is required, add authorization and restricted roles, bind commits to reviewed state, and replace destructive sample recovery with a separately authorized recovery policy.
