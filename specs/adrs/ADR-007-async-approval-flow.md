# ADR-007: Async Approval Flow via LangGraph Checkpointer + FastAPI Webhook

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The pipeline must pause after sending a draft to Telegram and wait for user approval — potentially for hours or days. The pipeline cannot block a process in memory during this wait.

The approval actions are:
- **Approve** → publish the draft as-is
- **Reject** → discard the signal, mark as rejected
- **Edit** → user sends free-text correction; pipeline re-generates a new draft incorporating the instruction
- **Regenerate** → generate a new draft from scratch for the same signal

## Decision

Use **LangGraph's built-in checkpointer** (`PostgresSaver`) to serialize full pipeline state to PostgreSQL when the pipeline reaches the approval node. The process then exits.

When the user replies in Telegram, the Telegram bot webhook (FastAPI endpoint) receives the message, identifies the `thread_id` from the message context, loads the graph state from PostgreSQL, and resumes execution.

Flow:
```
Pipeline run → ... → send Telegram draft → serialize state (PostgresSaver) → exit

Telegram reply → FastAPI webhook → resume graph from checkpoint (thread_id)
  → Approve: publish node → done
  → Reject: mark signal rejected → done
  → Edit: re-run draft node with correction instruction → re-send to Telegram → serialize → exit
  → Regenerate: re-run draft node with no prior draft → re-send to Telegram → serialize → exit
```

The `thread_id` is embedded in the Telegram message (e.g. as a callback_data or in the message text as a short ID) so the webhook can resolve it.

## Consequences

- No in-memory state held between pipeline run and approval — fully stateless between turns
- PostgreSQL is the only persistence layer needed (no Redis, no separate queue)
- Edit and Regenerate loops naturally re-enter the pipeline at the draft node
- Multiple pending approvals can coexist (each has its own `thread_id` and checkpoint)
- FastAPI is required for the Telegram webhook — this is the only reason a web server exists in Phase 1
