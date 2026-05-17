variable "project" {}
variable "github_org" {}
variable "github_repo" {}
variable "ar_location" {}
variable "ar_repo_id" {}

# ── Service Accounts ─────────────────────────────────────────────────────────

resource "google_service_account" "webhook" {
  project      = var.project
  account_id   = "sa-webhook"
  display_name = "Social Assistant — Webhook Service"
}

resource "google_service_account" "pipeline" {
  project      = var.project
  account_id   = "sa-pipeline"
  display_name = "Social Assistant — Pipeline Runner"
}

resource "google_service_account" "deploy" {
  project      = var.project
  account_id   = "sa-deploy"
  display_name = "Social Assistant — GitHub Actions Deploy"
}

resource "google_service_account" "scheduler" {
  project      = var.project
  account_id   = "sa-scheduler"
  display_name = "Social Assistant — Cloud Scheduler"
}

# ── IAM for runtime SAs ──────────────────────────────────────────────────────

locals {
  runtime_sa_roles = toset([
    "roles/cloudsql.client",
    "roles/aiplatform.user",
  ])
}

resource "google_project_iam_member" "webhook_roles" {
  for_each = local.runtime_sa_roles
  project  = var.project
  role     = each.key
  member   = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_project_iam_member" "pipeline_roles" {
  for_each = local.runtime_sa_roles
  project  = var.project
  role     = each.key
  member   = "serviceAccount:${google_service_account.pipeline.email}"
}

# ── IAM for deploy SA (GitHub Actions) ───────────────────────────────────────

resource "google_project_iam_member" "deploy_run_developer" {
  project = var.project
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# Allow deploy SA to act as the runtime SAs (needed for Cloud Run deploy)
resource "google_service_account_iam_member" "deploy_as_webhook" {
  service_account_id = google_service_account.webhook.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "deploy_as_pipeline" {
  service_account_id = google_service_account.pipeline.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

# Push to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "deploy_writer" {
  project    = var.project
  location   = var.ar_location
  repository = var.ar_repo_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deploy.email}"
}

# ── Cloud Scheduler IAM ───────────────────────────────────────────────────────

resource "google_project_iam_member" "scheduler_invoker" {
  project = var.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

# ── Workload Identity Federation (GitHub Actions → deploy SA) ─────────────────

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  # Only tokens from this repo can impersonate the deploy SA
  attribute_condition = "assertion.repository == '${var.github_org}/${var.github_repo}'"
}

resource "google_service_account_iam_member" "wif_deploy" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_org}/${var.github_repo}"
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "webhook_email"   { value = google_service_account.webhook.email }
output "pipeline_email"  { value = google_service_account.pipeline.email }
output "deploy_email"    { value = google_service_account.deploy.email }
output "scheduler_email" { value = google_service_account.scheduler.email }

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
