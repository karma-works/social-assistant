# ADR-003: Cron-Based Daily Scheduling

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The pipeline needs a trigger mechanism to periodically check for new signals (GitHub events, new repo activity, star jumps) and initiate pipeline runs.

Two options were considered:

**Option A — Cron/schedule**: Run the pipeline once per day (or configurable interval). Simple, predictable, no webhook infrastructure.

**Option B — Event-driven**: GitHub webhooks, RSS feeds, real-time triggers. Lower latency, but requires public webhook endpoints, webhook registration per repo, and more infrastructure.

## Decision

Use **cron-based daily scheduling** for Phase 1.

The signals being tracked (star jumps, releases, new repos) are not time-sensitive to the minute or hour. A 24h polling window is appropriate. Daily runs keep API call volume low and avoid rate limit pressure.

Scheduler: APScheduler embedded in the FastAPI service (which already exists for the Telegram webhook, see ADR-007). No separate scheduler service needed.

## Consequences

- No webhook infrastructure, no public endpoint registration per repo
- Predictable daily cost (one pipeline run per day)
- Up to 24h delay between a GitHub event and a draft being generated — acceptable for this use case
- Can migrate to event-driven (GitHub webhooks) in Phase 2 without changing the pipeline itself — only the trigger changes
