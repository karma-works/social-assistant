# social-assistant

<p align="center">
  <img src="logo.svg" width="140" alt="social-assistant logo" />
</p>

<p align="center">
  AI social media agent with human-in-the-loop approval.<br/>
  LangGraph pipeline for honest, source-backed post generation on Bluesky and X.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"/></a>
  <img src="https://img.shields.io/badge/python-3.13-blue" alt="Python 3.13"/>
  <img src="https://img.shields.io/badge/LangGraph-pipeline-orange" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/deploy-Cloud%20Run-4285F4" alt="Cloud Run"/>
</p>

---

## What it does

social-assistant watches your GitHub repositories for meaningful signals (star jumps, new releases), generates platform-specific draft posts, runs quality checks, and sends them to you via Telegram for approval. You approve, edit, or reject — nothing is published without your explicit confirmation.

**Key properties:**
- **Honest by design** — drafts must cite primary sources; hype and verbatim reposting are prohibited
- **Human-gated** — every post requires explicit Telegram approval before publishing
- **Platform-aware** — separate drafts for Bluesky (≤300 chars) and X (≤280 chars)
- **Configurable** — brand voice, signal thresholds, and platform toggles in `config.yaml`

## Architecture

```
GitHub API
    │
    ▼
[ Ingest ] ──► [ Deduplicate ] ──► [ Draft ] ──► [ QA ] ──► [ Telegram approval ]
                                                                     │
                                                              approve / edit / reject
                                                                     │
                                                                     ▼
                                                             [ Publish ] ──► Bluesky + X
```

The pipeline is a [LangGraph](https://github.com/langchain-ai/langgraph) state machine backed by Neon Postgres (persistent checkpointing). It runs as a Cloud Run Job triggered daily via Cloud Scheduler (or manually via GitHub Actions).

A FastAPI webhook service handles Telegram bot interactions for the approval flow.

## Stack

| Layer | Technology |
|---|---|
| Pipeline | Python 3.13, LangGraph, Gemini 3.1 Pro (Vertex AI) |
| Webhook | FastAPI, python-telegram-bot |
| Database | Neon (serverless Postgres) |
| Infra | Google Cloud Run, Cloud Scheduler, Secret Manager |
| IaC | Terraform |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Social | Bluesky AT Protocol, X OAuth 1.0a (tweepy) |

## Project layout

```
pipeline/       LangGraph pipeline: nodes, tools, state, graph
bot/            Telegram webhook + polling server (FastAPI)
prompts/        Versioned LLM prompts (draft generation, QA, brand voice)
infra/          Terraform modules (Cloud Run, IAM, secrets, scheduler)
migrations/     SQL schema migrations
config.yaml     Per-environment runtime config (models, thresholds, platform toggles)
wiki/           Project notes and learnings
```

## Local development

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Configure secrets
cp .env.example .env
# fill in GITHUB_TOKEN, TELEGRAM_*, BLUESKY_*, X_*, DATABASE_URL

# 3. Run migrations
psql "$DATABASE_URL" -f migrations/001_initial.sql

# 4. Run the pipeline locally
python -m pipeline.runner

# 5. Run the webhook (for Telegram approvals)
uvicorn bot.telegram_webhook:app --reload
```

## Deployment

Infrastructure is managed with Terraform. Application code is deployed via GitHub Actions on every push to `main`.

```bash
# Provision infrastructure (first time)
cd infra
terraform init
terraform apply

# Trigger pipeline manually
# → GitHub Actions → "Run Pipeline" workflow_dispatch
```

Secrets are stored in GCP Secret Manager and injected at runtime — never in environment files or code.

## Configuration

Edit `config.yaml` to control:

- **GitHub signal thresholds** (`star_jump_pct_7d`, `star_jump_abs_24h`, `star_cooldown_days`)
- **Platform toggles** (`platforms.bluesky.enabled`, `platforms.x.enabled`)
- **LLM models** (`pipeline.model`, `pipeline.model_fast`)
- **QA retries** (`pipeline.max_qa_retries`)

## License

[MIT](LICENSE)
