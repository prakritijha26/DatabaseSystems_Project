---
id: 20261021125641
title: offline-query-fidelity
principal: unknown
interest: unknown
hotspot: mock_engine.py,app.py,scenarios.json
business_capability: simulation
payoff_trigger: Review 3 offline demonstration acceptance
quadrant: prudent-inadvertent
category: code_quality
ai_authored: true
created: 2026-10-21
---

Offline fallback uses historical substring-matched fixtures rather than evaluating SQL, and its six tracks differ from the current scenario data. SELECT ignores projection and predicates, DML ignores predicates, and generic inputs can receive successful illustrative results; app.py labels these as mock but retains success statuses. Align supported fixtures with the current scenarios and reject unsupported offline queries consistently; full PostgreSQL fidelity remains unverified.
