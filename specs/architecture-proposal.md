## Architecture Proposal

Build a **LangGraph-based AI social media agent** with strict human approval before publishing.

### Core Flow

```text
Trigger / Schedule
→ Ingest Signals
→ Normalize + Deduplicate
→ Resolve Primary Sources
→ Extract Facts + Claims
→ Score Post Worthiness
→ Generate Draft
→ Generate / Attach Media
→ Run Quality Gates
→ Send Human Approval Request
→ Publish only after Approval
→ Store Feedback + Metadata
```

### Main Agents

* **GitHub Agent**: reads repos, README, stars, releases, demos, commits.
* **Website Agent**: reads personal homepage, project pages, blogs.
* **Social Signal Agent**: detects reposts/shared tweets and linked sources.
* **Source Resolver Agent**: finds primary sources; treats tweets as secondary.
* **Summarizer Agent**: rewrites external content in original wording.
* **Draft Agent**: generates posts using a configurable master prompt.
* **Media Agent**: creates screenshots, diagrams, charts, or images.
* **QA Agent**: validates factuality, sources, honesty, copyright, style, format.

### Style System

Do **not** learn style from old tweets.

Use versioned prompt configs:

```text
prompts/
  master_style.md
  post_generation.md
  quality_gate.md
```

The master prompt defines tone, anti-hype rules, honesty rules, formatting, and platform-specific constraints.

### Data Model

Store every candidate with:

```text
Signal
- source type
- normalized summary
- primary sources
- secondary sources
- factual claims
- project status
- generated draft
- media assets
- QA result
- approval status
- publish metadata
```

### Human-in-the-Loop

Send proposal via Telegram or email.

User actions:

```text
Approve → publish
Reject → discard
Edit → update draft
Regenerate → create new variant
```

Publishing must never happen without explicit approval.

### Quality Gates

Before approval, check:

* no copied repost text
* primary sources included
* claims are source-backed
* project status is honest
* no fake traction
* style matches master prompt
* platform length/format is valid
* media is relevant and non-misleading

### Evals

Create reusable eval datasets for:

* source attribution
* repost summarization
* anti-copying
* factuality
* project honesty
* style compliance
* X/Bluesky formatting
* media relevance
* approval-before-publish behavior

### Suggested Stack

```text
Python
LangChain
LangGraph
FastAPI
PostgreSQL
pgvector or Qdrant
Redis / queue
GitHub API
X API or careful manual/API-assisted flow
Bluesky API
Telegram Bot API
Email provider
Docker
GitHub Actions
```

### Implementation Phases

1. GitHub + website ingestion → post draft → Telegram approval.
2. Add repost/research ingestion and primary-source resolution.
3. Add media generation, evals, QA scoring, analytics, and feedback learning.
