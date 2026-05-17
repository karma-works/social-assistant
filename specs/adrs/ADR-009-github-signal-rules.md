# ADR-009: GitHub Signal Detection Rules

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The GitHub ingestion node polls tracked repositories daily and must decide which events are "post-worthy." Too sensitive = noise and duplicate posts. Too conservative = missed genuine news.

The ingestion node checks the GitHub API for each tracked repo and produces a list of `Signal` objects for the pipeline to process.

## Decision

Three signal types are post-worthy in Phase 1:

### 1. New Release / Tag Published
- Trigger: a new GitHub release (not pre-release) was published since the last pipeline run
- Always post-worthy — this is the highest-signal event
- Content: release title, description, changelog summary, repo name, stars

### 2. Star Jump
- Trigger: star count increased by **≥50% in the last 7 days** OR **≥100 absolute in the last 24h**
- Both thresholds are configurable in `config.yaml`
- Only one "star jump" post per repo per 30-day window (cooldown enforced in the dedup node)
- Content: current star count, delta, growth rate, repo description

### 3. New Repository Created
- Trigger: a tracked GitHub user/org published a new public repository
- Requirements: non-empty README **and** a repository description set
- Repos with no README or no description are skipped (not ready to communicate about)
- Content: repo name, description, README summary, language, topics

### Not post-worthy (Phase 1)
- Routine commits to main
- README-only edits
- Issue or discussion activity
- Pre-release tags
- Fork counts, watcher counts

## Consequences

- Clear, auditable rules — easy to add/remove signal types without changing pipeline structure
- Thresholds are config-driven, not hard-coded
- The 30-day cooldown on star jumps prevents repeated posts about the same traction story
- Phase 2 can add signals (meaningful commits, blog posts, research mentions) by extending the ingestion node
