# ADR-001: Single LangGraph Pipeline over Multi-Agent System

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The initial vision described 8 specialized sub-agents (GitHub Agent, Website Agent, Source Resolver, Summarizer, Draft Agent, Media Agent, QA Agent, Social Signal Agent) coordinating as a multi-agent system.

Recent research ("Towards a Science of Scaling Agent Systems", arXiv:2512.08296) demonstrates that multi-agent systems consistently degrade performance on tool-heavy sequential workflows — exactly the shape of this pipeline. The study found a tool-coordination trade-off (β=−0.096, p=0.002) where efficiency penalties compound as environmental complexity increases. Independent multi-agent coordination amplifies errors 17.2× versus 4.4× for centralized designs.

The core flow of this system is inherently sequential:
```
Ingest → Normalize → Dedup → Resolve → Draft → QA → Approve → Publish
```
This is a state machine, not a collaboration or exploration problem. The named "agents" are pipeline stages with tool access, not independent reasoning loci.

## Decision

Use a **single LangGraph state machine** with specialized tool nodes. Each stage (ingestion, deduplication, draft generation, QA, approval, publishing) is a LangGraph node. Tools (GitHub API, Bluesky API, LLM calls) are called within nodes, not delegated to sub-agents.

## Consequences

- No inter-agent coordination overhead or error propagation between agents
- Full shared state across all pipeline stages — no lossy message compression
- Simpler debugging: one execution graph, one checkpointer, one state schema
- LangGraph's built-in interrupt/resume handles the async approval step cleanly
- Genuine parallelism (e.g. processing multiple signals simultaneously) can be added later via LangGraph's `Send` API without restructuring into full multi-agent
