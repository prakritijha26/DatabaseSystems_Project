---
id: 20261021125641
title: launcher-ddl-validation
principal: unknown
interest: unknown
hotspot: engine.py,start_demo.sh,tests/test_adapter.py
business_capability: demo
payoff_trigger: Review 3 six-track web acceptance
quadrant: prudent-inadvertent
category: testing
ai_authored: true
created: 2026-10-21
---

The launcher selects the virtualenv interpreter, where WHAT_IF ALTER TABLE marks DROP COLUMN score is rejected as a nested modifying statement before database access. The requested system-Python demos pass through the mock path, masking this runtime difference; the contract harness also accepts error-shaped reports. Correct the AST handling for permitted DROP COLUMN and verify all six tracks with the launcher interpreter, including real PostgreSQL acceptance when port 5432 is available.

## Resolution — 2026-10-21
The direct DROP COLUMN child AST is now accepted while nested modifying statements remain rejected. Focused transaction tests cover the permitted DDL and preserve RESTRICT for APPLY. Real PostgreSQL acceptance remains unverified because no server is available.
