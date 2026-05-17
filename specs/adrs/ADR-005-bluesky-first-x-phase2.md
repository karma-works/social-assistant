# ADR-005: Bluesky-First Publishing, X in Phase 2

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The target platforms are Bluesky and X (Twitter). They have significantly different API landscapes:

- **Bluesky (AT Protocol)**: Open API, no authentication cost, no write limits for normal usage, read access is fully free.
- **X (Twitter)**: Free tier allows ~1500 tweet writes/month (sufficient), but read access is heavily restricted and paid. API reliability and pricing have been volatile.

Both platforms require platform-specific post formatting (character limits, link handling, thread structure).

## Decision

**Phase 1: Bluesky only.** The publishing node, post formatter, and platform constraints are implemented for Bluesky exclusively.

**Phase 2: Add X.** Once the core pipeline is proven end-to-end on Bluesky, the X publishing node is added. The pipeline's platform abstraction (each platform is a publish target with its own formatter) allows this without restructuring.

## Consequences

- Faster MVP with one platform to integrate and test
- No X API costs or rate limit concerns in Phase 1
- Bluesky's open API makes testing and development easier (can read own posts for manual verification)
- X publishing in Phase 2 is additive — the pipeline node interface is designed to be platform-agnostic from the start
