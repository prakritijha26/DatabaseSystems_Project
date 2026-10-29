---
id: 20261014230302
title: live-demo-boundary
principal: unknown
interest: unknown
hotspot: app.py,engine.py,src/app.ts
business_capability: simulation
payoff_trigger: Live engine supports catalog tracing and agreed academic metrics
quadrant: prudent-deliberate
category: migration
ai_authored: true
created: 2026-10-14
---

Keep the raw live DML engine behind an ImpactReport adapter and label connection-failure mock fallback explicitly (docs/adr/0001-impact-report-adapter.md). Live schema uses enrollment IDs and weighted score, while original offline fixtures model CGPA and DDL dependencies. Until live catalog tracing and the agreed metric model are delivered, unsupported live DDL/SELECT requests return errors; no fixture results may masquerade as live evidence.

## Review 2 resolution — 2026-10-15
Live DDL, catalog tracing, SELECT and shared schema-compatible scenarios are implemented and verified. The remaining trusted-schema/production boundary is tracked by ADR 0002 and the review-two-boundary entry. Explicit offline labeling remains supported.
