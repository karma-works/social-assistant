# ADR-006: X Publishing Strategy — Free Tier with Browser Automation Fallback

**Status:** Accepted  
**Date:** 2026-05-17

## Context

X's free API tier allows ~1500 tweet writes/month. At ~7 posts/week (~30/month), this is sufficient with significant headroom. Read access is not needed (ADR-004). The goal is zero API cost in normal operation.

Browser automation (e.g. via Playwright) is a fallback if the free tier becomes unusable. Risks: fragile (UI changes break it), against X's ToS, requires managing session state/cookies. It is not a preferred path but is a viable last resort.

## Decision

**Use X API free tier for publishing.** Store credentials as environment variables. The X publishing node uses the official API only.

**Browser automation is documented as a fallback** but not implemented until the free tier proves inadequate. The publishing node interface is designed so the transport layer (API vs. browser) can be swapped without changing the pipeline.

Known free tier constraints to respect:
- 1500 writes/month (well within budget at ~30/month)
- No media upload via free tier — Phase 2 posts will be text-only on X until a paid tier is justified
- Rate limit: 50 requests per 15-minute window for writes

## Consequences

- Zero API cost for X publishing at current volume
- Media attachments on X deferred until volume or requirements justify an upgrade
- Browser automation remains a documented escape hatch, not a first-class implementation
- If X API pricing changes again, the fallback path is pre-scoped
