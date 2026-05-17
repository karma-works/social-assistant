# ADR-002: LLM-Based Semantic Deduplication over Vector Store

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The pipeline must avoid generating posts about topics that were already covered recently. Two sources of duplication exist:

1. A new signal (e.g. GitHub star jump) is about a project already posted about on Bluesky recently.
2. A topic appears in multiple signals in the same pipeline run (e.g. a release commit + a star jump for the same repo).

Two implementation options were considered:

**Option A — LLM semantic check**: Pull recent stored posts from PostgreSQL, include them in an LLM prompt alongside the new signal, ask "is this the same topic as any of these?" No additional infrastructure.

**Option B — Vector similarity**: Embed every signal and post, store embeddings in pgvector or Qdrant, use cosine similarity threshold. Faster at scale, deterministic, but adds infra and embedding costs.

## Decision

Use **LLM-based semantic deduplication (Option A)**.

At ~7 posts/week (~350/year), the full post history is small enough to include directly in a prompt window. No vector store is needed. The LLM check runs once per signal per pipeline execution.

Bluesky and X post history will not be read via social APIs. Instead, all posts sent by social-assistant are stored in PostgreSQL at publish time and used as the deduplication source of truth (see ADR-004).

## Consequences

- No pgvector, Qdrant, or embedding model needed in Phase 1
- Small additional token cost per pipeline run (~few hundred tokens for post history context)
- Dedup logic is auditable — the LLM's reasoning is visible in the trace
- At higher volume (phase 3+), can migrate to vector similarity without changing the pipeline interface — the dedup node's contract is the same either way
