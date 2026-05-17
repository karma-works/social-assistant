# ADR-004: Local Post Store as Deduplication Source of Truth

**Status:** Accepted  
**Date:** 2026-05-17

## Context

Deduplication (ADR-002) requires knowing what has already been posted. The two options are:

1. **Read from social APIs** (Bluesky timeline, X timeline) — real-time truth, but X's free tier has severe read restrictions, and Bluesky reads add latency and a dependency on API availability.
2. **Store posts locally at publish time** — social-assistant writes every published post to PostgreSQL. Dedup checks against this local store instead of hitting social APIs.

The assumption is that 95%+ of posts on these accounts will be published by social-assistant. Manual posts are the exception.

## Decision

**Store all published posts in PostgreSQL at publish time.** The local store is the source of truth for deduplication. Social APIs are never called for dedup purposes.

Schema (posts table):
- `id`, `platform` (bluesky/x), `topic_summary`, `content`, `signal_id`, `published_at`, `metadata` (JSON)

The `topic_summary` field is a short LLM-generated description of what the post is about — used as the dedup comparison target (not the raw post text).

## Consequences

- No social API reads needed → zero API cost for dedup
- Dedup works even when social APIs are down or rate-limited
- Manual posts not tracked by social-assistant will not be considered for dedup — acceptable given the 95% assumption
- If the assumption breaks (significant manual posting), a one-time import script can backfill the store from Bluesky's API (which is open and free to read)
