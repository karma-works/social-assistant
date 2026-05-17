# ADR-010: GCP Deployment Architecture

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The final deployment target is Google Cloud Platform. The system has two distinct runtime profiles:

1. **Event-driven (always-on)**: FastAPI Telegram webhook — receives Telegram callbacks and resumes paused pipeline executions. Must have low latency (Telegram retries on timeout) but very low traffic.
2. **Batch (scheduled)**: Daily pipeline run — ingest GitHub signals, generate drafts, send to Telegram. Runs once per day, typically 1–5 minutes.

These have different scaling requirements and cost profiles. Serving them from a single always-running container is wasteful; separating them allows each to scale independently.

## Decision

Deploy on GCP with the following service mapping:

| Component | GCP Service | Rationale |
|---|---|---|
| FastAPI (Telegram webhook) | **Cloud Run Service** | HTTP-triggered, scales to zero, auto-HTTPS, Telegram webhook URL is the `.run.app` endpoint |
| Daily pipeline run | **Cloud Run Job** | Batch execution, defined start/end, no idle cost |
| Daily trigger | **Cloud Scheduler** | Managed cron, calls Cloud Run Job via HTTPS |
| PostgreSQL (pipeline state + posts) | **Cloud SQL (PostgreSQL 16)** | Managed, automated backups, IAM auth |
| LangGraph checkpointer | **PostgresSaver on Cloud SQL** | No changes to pipeline code; Cloud SQL Python Connector handles auth |
| Secrets (tokens, credentials) | **Secret Manager** | No `.env` files in production; mounted as env vars at runtime |
| Docker images | **Artifact Registry** | GCP-native container registry |
| IaC | **Terraform** | Versioned, reproducible GCP resource definitions |
| CI/CD | **GitHub Actions** | Build → push to Artifact Registry → deploy Cloud Run |

### Networking

- Cloud SQL with **private IP** inside a VPC
- Cloud Run accesses Cloud SQL via the **Cloud SQL Python Connector** (handles IAM auth, no VPC connector required for the connector library)
- No public database exposure

### Service Accounts

- `sa-pipeline@PROJECT.iam.gserviceaccount.com`: Cloud Run Job service account
  - `roles/cloudsql.client`
  - `roles/secretmanager.secretAccessor`
  - `roles/aiplatform.user` (for Vertex AI)
- `sa-webhook@PROJECT.iam.gserviceaccount.com`: Cloud Run Service service account
  - `roles/cloudsql.client`
  - `roles/secretmanager.secretAccessor`
  - `roles/run.invoker` (to invoke the pipeline job on demand if needed)

### Terraform Layout

```
infra/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── cloud-run/
│   ├── cloud-sql/
│   ├── cloud-scheduler/
│   └── secret-manager/
└── environments/
    ├── dev/
    └── prod/
```

## Consequences

- Zero idle cost for pipeline (Cloud Run Job only runs once/day)
- Minimal idle cost for webhook (Cloud Run Service scales to zero between Telegram callbacks)
- Cloud SQL is the only always-running (billable) resource (~$10–20/month for `db-f1-micro`)
- Telegram webhook gets an auto-provisioned HTTPS URL from Cloud Run — no cert management
- GitHub Actions CI/CD: push to `main` triggers build, push to Artifact Registry, and Cloud Run Service redeploy
- Cloud Run Job gets updated image on next scheduled run (or manual trigger for immediate redeploy)
