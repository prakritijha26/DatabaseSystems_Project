---
id: 20261015073355
title: compose-runtime-check
principal: unknown
interest: unknown
hotspot: docker-compose.yml
business_capability: team-deployment
payoff_trigger: A session with working Docker Engine socket and Compose v2 access
quadrant: prudent-deliberate
category: testing
ai_authored: true
created: 2026-10-15
---

Compose configuration and mounted initialization paths are validated, but this session cannot access the Docker socket and has no Compose plugin. Real acceptance evidence was collected on an isolated native PostgreSQL 15.15 built from official source, not postgres:15-alpine. Run docker compose up -d --wait on a fresh project volume and rerun the live scenarios when Docker access is available; never erase an existing data volume to make this check pass.
