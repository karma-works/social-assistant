terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  backend "gcs" {
    # bucket = set in environments/dev/backend.tf
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

module "cloud_sql" {
  source     = "./modules/cloud-sql"
  project    = var.project
  region     = var.region
  name       = "${var.env}-social-assistant-db"
  tier       = var.db_tier
}

module "artifact_registry" {
  source  = "./modules/artifact-registry"
  project = var.project
  region  = var.region
}

module "service_accounts" {
  source  = "./modules/service-accounts"
  project = var.project
}

module "secrets" {
  source  = "./modules/secret-manager"
  project = var.project
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
}

module "cloud_scheduler" {
  source          = "./modules/cloud-scheduler"
  project         = var.project
  region          = var.region
  pipeline_job_id = "social-assistant-pipeline"
  cron_schedule   = var.pipeline_cron
}
