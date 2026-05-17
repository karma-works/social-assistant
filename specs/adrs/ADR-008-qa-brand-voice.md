# ADR-008: QA Node with Brand Voice Style Check

**Status:** Accepted  
**Date:** 2026-05-17

## Context

Generated drafts must be validated before being sent for approval. Two categories of checks are needed:

1. **Factuality/integrity checks**: no copied text, claims are source-backed, project status is honest, no fake traction, platform length/format valid.
2. **Style compliance**: draft matches the brand voice defined in `prompts/brand_voice.md`.

Brand voice is authored by the user as a versioned markdown document. No labeled training data or automated style classifier exists.

## Decision

The **QA node runs a single LLM call** with:
- The generated draft
- The full `prompts/brand_voice.md` content
- The source signal summary and factual claims
- A structured scoring rubric

The LLM returns a structured result:
```json
{
  "style_score": 1-5,
  "style_issues": ["..."],
  "factuality_pass": true/false,
  "factuality_issues": ["..."],
  "format_pass": true/false,
  "format_issues": ["..."],
  "overall": "pass" | "warn" | "fail"
}
```

**Pass**: proceed to approval.  
**Warn**: proceed to approval with QA notes surfaced in the Telegram message so the user sees them.  
**Fail**: re-enter draft node with QA feedback as correction instruction (max 2 retries before discarding).

Style threshold: score ≥ 3 = pass, score 2 = warn, score 1 = fail.

## Consequences

- No ground truth labels or training data required
- Brand voice changes take effect immediately (just edit the markdown file)
- QA issues are visible to the user in Telegram — they see both the draft and any warnings
- Two-retry limit on QA failures prevents infinite loops
- Style scoring is subjective and LLM-dependent — acceptable given human approval is always the final gate
