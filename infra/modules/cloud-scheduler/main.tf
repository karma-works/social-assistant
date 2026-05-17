variable "project" {}
variable "region" {}
variable "pipeline_job_id" {}
variable "cron_schedule" { default = "0 8 * * *" }

resource "google_cloud_scheduler_job" "pipeline" {
  name      = "trigger-social-assistant-pipeline"
  region    = var.region
  schedule  = var.cron_schedule
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project}/jobs/${var.pipeline_job_id}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

resource "google_service_account" "scheduler" {
  account_id   = "sa-scheduler"
  display_name = "Cloud Scheduler — triggers pipeline job"
}

resource "google_project_iam_member" "scheduler_run_invoker" {
  project = var.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}
