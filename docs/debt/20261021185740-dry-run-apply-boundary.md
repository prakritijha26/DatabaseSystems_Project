---
id: 20261021185740
title: dry-run-apply-boundary
principal: unknown
interest: unknown
hotspot: engine.py,app.py,src/cli.ts,docs/adr/0003-dry-run-apply.md
business_capability: permanent-execution
payoff_trigger: Deployment outside a dedicated local demonstration database or concurrent review-to-apply consistency requirements
quadrant: prudent-deliberate
category: infrastructure
ai_authored: true
created: 2026-10-21
---

ADR 0003 permits separate dry-run and apply transactions in a trusted local demo, without binding APPLY to the earlier snapshot or providing distributed two-phase commit. Recovery rebuilds the named sample schema with CASCADE and must remain confined to a dedicated demonstration database. Before broader use, add authorization and restricted roles, reviewed-state binding, and a separately authorized recovery policy; ambiguous permanent-command outcomes require read-back, while mock acknowledgements never establish persistence.
