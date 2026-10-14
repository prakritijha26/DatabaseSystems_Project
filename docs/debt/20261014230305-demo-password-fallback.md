---
id: 20261014230305
title: demo-password-fallback
principal: unknown
interest: unknown
hotspot: engine.py
business_capability: database-connection
payoff_trigger: Deployment beyond the local course demonstration
quadrant: prudent-deliberate
category: infrastructure
ai_authored: true
created: 2026-10-14
---

Retain the user-requested local demonstration password fallback when PGPASSWORD is absent. Environment configuration and explicit password arguments override it. Remove the embedded fallback and use a restricted simulation database role before deploying outside the local course environment; rollback does not undo sequence advances or external effects of arbitrary database functions and triggers.
