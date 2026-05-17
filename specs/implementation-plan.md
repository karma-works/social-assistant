# social-assistant — Implementation Plan

**Last updated:** 2026-05-17 (deployment target: GCP / Vertex AI)  
**Working title:** social-assistant

## Goal

A LangGraph pipeline that detects new signals from GitHub, generates honest draft social posts, runs QA, requests human approval via Telegram, and publishes to Bluesky (X in Phase 2).

## Architecture (locked)

Single LangGraph state machine. No multi-agent coordination.  
See ADRs in `specs/adrs/` for all architectural decisions.

```
[Cron Trigger]
      ↓
[Ingest GitHub Signals]
      ↓
[Deduplicate Signals]  ← checks local PostgreSQL post store
      ↓
[Generate Draft]       ← uses brand_voice.md + signal facts
      ↓
[QA Node]              ← factuality + style check (brand_voice.md in prompt)
      ↓ (fail → retry draft, max 2x)
[Send Telegram Approval]
      ↓ (pipeline state serialized to PostgreSQL, process exits)

[Telegram Reply] → FastAPI Webhook
      ↓
[Resume from Checkpoint]
      ├─ Approve  → [Publish to Bluesky] → [Store post] → done
      ├─ Reject   → [Mark signal rejected] → done
      ├─ Edit     → [Re-run Draft with correction] → [QA] → [Send Telegram]
      └─ Regenerate → [Re-run Draft from scratch] → [QA] → [Send Telegram]
```

## Tech Stack

| Layer | Technology |
|---|---|
| Pipeline | Python, LangGraph |
| LLM | Gemini 3.1 Pro via Vertex AI (`langchain-google-vertexai`) |
| LLM (fast ops) | Gemini 3.1 Flash-Lite via Vertex AI (dedup, topic summary) |
| LLM auth | GCP service account IAM — no API key needed |
| Web server | FastAPI (Telegram webhook only) |
| Scheduler | **Cloud Scheduler** (GCP managed cron) |
| Database | **Cloud SQL PostgreSQL 16** (private IP) |
| State persistence | LangGraph `PostgresSaver` + Cloud SQL Python Connector |
| Social: Bluesky | `atproto` Python SDK |
| Social: X | `tweepy` (Phase 2) |
| Approval channel | Telegram Bot API |
| Config | `config.yaml` + **Secret Manager** (no `.env` in production) |
| Deployment (prod) | **Cloud Run Service** (webhook) + **Cloud Run Job** (pipeline) |
| Deployment (local) | Docker Compose (unchanged) |
| Container registry | **Artifact Registry** |
| IaC | **Terraform** (`infra/`) |
| CI/CD | **GitHub Actions** → Artifact Registry → Cloud Run |

## Project Layout

```
social-assistant/
├── pipeline/
│   ├── graph.py              # LangGraph graph definition
│   ├── state.py              # Typed pipeline state schema
│   ├── nodes/
│   │   ├── ingest_github.py
│   │   ├── dedup.py
│   │   ├── draft.py
│   │   ├── qa.py
│   │   ├── telegram_send.py
│   │   └── publish.py
│   └── tools/
│       ├── github_api.py
│       ├── bluesky_api.py
│       └── x_api.py          # Phase 2
├── bot/
│   └── telegram_webhook.py   # FastAPI app + webhook handler
├── prompts/
│   ├── brand_voice.md        # Authored by user, versioned
│   ├── draft_generation.md
│   └── qa_check.md
├── infra/                    # Terraform
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── cloud-run/
│   │   ├── cloud-sql/
│   │   ├── cloud-scheduler/
│   │   └── secret-manager/
│   └── environments/
│       ├── dev/
│       └── prod/
├── .github/
│   └── workflows/
│       └── deploy.yml        # build → Artifact Registry → Cloud Run
├── config.yaml               # Thresholds, tracked repos, settings
├── .env.example              # Local dev template (no real secrets)
├── Dockerfile.webhook        # Cloud Run Service
├── Dockerfile.pipeline       # Cloud Run Job
├── docker-compose.yml        # Local dev only
└── tests/
    ├── test_ingest.py
    ├── test_dedup.py
    ├── test_draft.py
    └── test_qa.py
```

## Pipeline State Schema

```python
class PipelineState(TypedDict):
    run_id: str
    signals: list[Signal]          # raw signals from ingestion
    active_signal: Signal | None   # signal currently being processed
    draft: str | None              # current draft text
    qa_result: QAResult | None
    qa_retries: int
    approval_status: str | None    # pending/approved/rejected/edit/regenerate
    edit_instruction: str | None   # free-text correction from user
    published_post_id: str | None
    error: str | None
```

## Database Schema

```sql
-- Tracked signals
CREATE TABLE signals (
    id UUID PRIMARY KEY,
    source TEXT,           -- 'github_release' | 'github_stars' | 'github_new_repo'
    repo TEXT,
    topic_summary TEXT,    -- LLM-generated, used for dedup
    raw_data JSONB,
    detected_at TIMESTAMP,
    status TEXT            -- 'pending' | 'approved' | 'rejected' | 'discarded'
);

-- Published posts (source of truth for dedup)
CREATE TABLE posts (
    id UUID PRIMARY KEY,
    signal_id UUID REFERENCES signals(id),
    platform TEXT,         -- 'bluesky' | 'x'
    topic_summary TEXT,
    content TEXT,
    published_at TIMESTAMP,
    platform_post_id TEXT,
    metadata JSONB
);

-- LangGraph checkpointer tables (managed by PostgresSaver)
-- created automatically by LangGraph
```

---

## Phase 1: Core Pipeline (MVP)

**Goal:** GitHub → draft → Telegram approval → Bluesky publish. Proven end-to-end.

### Milestone 0: GCP Bootstrap (do once, before any code)
- [ ] GCP project created, billing enabled
- [ ] Enable APIs: Cloud Run, Cloud SQL, Cloud Scheduler, Secret Manager, Artifact Registry, Vertex AI
- [ ] Terraform state bucket (GCS) created manually
- [ ] Terraform modules scaffolded: `infra/modules/{cloud-run,cloud-sql,cloud-scheduler,secret-manager}`
- [ ] Terraform `environments/dev/` applied: Cloud SQL instance, Artifact Registry repo, service accounts
- [ ] Service accounts provisioned with minimal IAM roles (see ADR-010)
- [ ] Secrets created in Secret Manager: GitHub token, Bluesky credentials, Telegram bot token
- [ ] `gcloud auth application-default login` for local dev
- [ ] GitHub Actions workflow: build → push to Artifact Registry → deploy Cloud Run Service

### Milestone 1: Skeleton + Infra
- [ ] Project setup: Python, uv, Docker Compose (local dev only)
- [ ] `langchain-google-vertexai` + `google-cloud-aiplatform` replaces `anthropic` dependency
- [ ] Verify Gemini 3.1 Pro model ID in Vertex AI console; update `config.yaml`
- [ ] LangGraph graph skeleton with typed state (`state.py`)
- [ ] PostgreSQL schema migrations (runs against Cloud SQL in CI, local Docker Compose for dev)
- [ ] `config.yaml` structure: tracked repos, thresholds, model config
- [ ] `.env` template for local dev only (production uses Secret Manager)

### Milestone 2: GitHub Ingestion Node
- [ ] GitHub API client wrapper (`tools/github_api.py`)
- [ ] Detect new releases since last run (store last-seen release ID per repo)
- [ ] Detect star jumps (configurable: +50% in 7d or +100 absolute in 24h)
- [ ] Detect new repos (non-empty README + description)
- [ ] Persist signals to `signals` table
- [ ] Unit tests with mocked GitHub API responses

### Milestone 3: Deduplication Node
- [ ] Load recent posts from `posts` table (last 90 days)
- [ ] LLM semantic check: "is this signal about a topic already covered?"
- [ ] LLM generates `topic_summary` for each new signal
- [ ] Filter out duplicates; mark discarded signals in DB
- [ ] Unit tests: duplicate detection, new signal pass-through

### Milestone 4: Draft Generation Node
- [ ] `prompts/brand_voice.md` — initial version authored
- [ ] `prompts/draft_generation.md` — system prompt for draft node
- [ ] Draft node: generate platform-specific post (Bluesky: 300 chars, thread if needed)
- [ ] Draft includes: factual claims, source links, honest project status signals
- [ ] Unit tests with fixture signals

### Milestone 5: QA Node
- [ ] `prompts/qa_check.md` — structured scoring rubric
- [ ] QA node: single LLM call with draft + brand_voice.md + signal facts
- [ ] Returns structured JSON: style_score, factuality_pass, format_pass, overall
- [ ] Retry logic: fail → re-run draft node with QA feedback (max 2 retries)
- [ ] Unit tests: pass/warn/fail cases

### Milestone 6: Telegram Approval Flow
- [ ] Telegram bot setup (BotFather, webhook URL)
- [ ] FastAPI app with `/telegram/webhook` endpoint
- [ ] Send draft to Telegram with inline keyboard: Approve / Reject / Edit / Regenerate
- [ ] LangGraph `PostgresSaver` checkpointer configured
- [ ] Pipeline serializes state at approval node and exits
- [ ] Webhook handler: parse reply, identify `thread_id`, resume graph from checkpoint
- [ ] Edit flow: capture free-text correction, re-enter draft node
- [ ] Integration test: full approve flow end-to-end

### Milestone 7: Bluesky Publishing Node
- [ ] `atproto` SDK client wrapper (`tools/bluesky_api.py`)
- [ ] Post formatter: Bluesky character limit, link cards, thread splitting
- [ ] Publish node: post to Bluesky, store result in `posts` table
- [ ] Integration test: publish a test post to a dev account

### Milestone 8: Cloud Scheduler + End-to-End Deploy
- [ ] Cloud Scheduler job configured via Terraform: daily at 08:00, triggers Cloud Run Job
- [ ] Cloud Run Job Dockerfile: pipeline entry point
- [ ] Cloud Run Service Dockerfile: FastAPI webhook entry point
- [ ] GitHub Actions: push to `main` → build both images → push to Artifact Registry → deploy Cloud Run Service (Job image updated on next scheduled run)
- [ ] Telegram webhook URL registered with BotFather: `https://<cloud-run-service>.run.app/telegram/webhook`
- [ ] Full end-to-end run on GCP dev environment: cron fires → ingestion → dedup → draft → QA → Telegram → approve → publish
- [ ] Local Docker Compose still works for development

---

## Phase 2: Extended Sources + X

**Goal:** Add more signal sources and X publishing.

- [ ] X publishing node (`tweepy`, free tier, text-only)
- [ ] Website/homepage ingestion (scrape personal site, detect new blog posts)
- [ ] Repost/research signal ingestion (arXiv, Hugging Face, detect shared content)
- [ ] Source resolver node (find primary sources from secondary/tweet references)
- [ ] Additional Cloud Scheduler jobs for per-source schedules (website weekly, GitHub daily)

---

## Phase 3: Media + Evals

**Goal:** Richer posts, automated quality measurement.

- [ ] Media generation: screenshots via Playwright, diagrams via Mermaid/code2flow
- [ ] Eval harness: reusable test datasets for source attribution, anti-copying, honesty, style
- [ ] Analytics: track approval rates, QA scores, rejection reasons over time
- [ ] Bluesky image attachment support
- [ ] Feedback loop: rejection reasons inform draft prompt tuning

---

## Configuration Reference (`config.yaml`)

```yaml
github:
  tracked_users: []         # GitHub usernames/orgs to watch
  tracked_repos: []         # explicit repo list (owner/repo)
  star_jump_pct_7d: 50      # % increase in 7 days = signal
  star_jump_abs_24h: 100    # absolute increase in 24h = signal
  star_cooldown_days: 30    # min days between star posts per repo

gcp:
  project: ""               # GCP project ID
  region: "us-central1"
  vertex_ai_location: "us-central1"

pipeline:
  max_qa_retries: 2
  model: "gemini-3.1-pro-preview"           # verify in Vertex AI console
  model_fast: "gemini-3.1-flash-lite"
  dedup_lookback_days: 90

scheduler:
  github_cron: "0 8 * * *"  # managed by Cloud Scheduler (Terraform)

platforms:
  bluesky:
    enabled: true
    handle: ""              # set in .env
  x:
    enabled: false          # Phase 2
```

---

## Non-Goals (explicitly out of scope for Phase 1)

- Media generation (Phase 3)
- Eval harness (Phase 3)
- X publishing (Phase 2)
- Website/blog ingestion (Phase 2)
- Learning from historical tweets (never — by design, see vision.md)
- Automatic publishing without human approval (never — by design)
