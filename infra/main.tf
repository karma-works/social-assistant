terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  backend "gcs" {}
}

provider "google" {
  project = var.project
  region  = var.region
}

# ── APIs ─────────────────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "aiplatform.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ── Artifact Registry ────────────────────────────────────────────────────────

module "artifact_registry" {
  source  = "./modules/artifact-registry"
  project = var.project
  region  = var.region
  repo_id = "social-assistant"

  depends_on = [google_project_service.apis]
}

# ── Service Accounts + IAM + Workload Identity Federation ───────────────────

module "service_accounts" {
  source      = "./modules/service-accounts"
  project     = var.project
  github_org  = var.github_org
  github_repo = var.github_repo
  ar_location = var.region
  ar_repo_id  = module.artifact_registry.repo_id

  depends_on = [google_project_service.apis, module.artifact_registry]
}

# ── Cloud SQL ────────────────────────────────────────────────────────────────

module "cloud_sql" {
  source  = "./modules/cloud-sql"
  project = var.project
  region  = var.region
  name    = "${var.env}-social-assistant"
  tier    = var.db_tier

  depends_on = [google_project_service.apis]
}

# ── Secret Manager ───────────────────────────────────────────────────────────

module "secrets" {
  source       = "./modules/secret-manager"
  project      = var.project
  secret_names = [
    "github-token",
    "telegram-bot-token",
    "telegram-chat-id",
    "bluesky-handle",
    "bluesky-password",
    "database-url",
  ]
  accessor_sa_emails = [
    module.service_accounts.webhook_email,
    module.service_accounts.pipeline_email,
  ]

  depends_on = [google_project_service.apis, module.service_accounts]
}

# ── Cloud Run (Service + Job) ────────────────────────────────────────────────

module "cloud_run" {
  source             = "./modules/cloud-run"
  project            = var.project
  region             = var.region
  db_connection_name = module.cloud_sql.connection_name
  webhook_sa_email   = module.service_accounts.webhook_email
  pipeline_sa_email  = module.service_accounts.pipeline_email
  artifact_registry  = "${var.region}-docker.pkg.dev/${var.project}/social-assistant"

  depends_on = [
    google_project_service.apis,
    module.service_accounts,
    module.cloud_sql,
    module.secrets,
  ]
}

# ── Cloud Scheduler ──────────────────────────────────────────────────────────

module "cloud_scheduler" {
  source          = "./modules/cloud-scheduler"
  project         = var.project
  region          = var.region
  pipeline_job_id = module.cloud_run.pipeline_job_name
  cron_schedule   = var.pipeline_cron
  scheduler_email = module.service_accounts.scheduler_email

  depends_on = [module.cloud_run, module.service_accounts]
}
