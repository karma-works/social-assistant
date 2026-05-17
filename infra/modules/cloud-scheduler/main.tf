variable "project" {}
variable "region" {}
variable "pipeline_job_id" {}
variable "cron_schedule" { default = "0 8 * * *" }
variable "scheduler_email" {}

resource "google_cloud_scheduler_job" "pipeline" {
  project   = var.project
  name      = "trigger-social-assistant-pipeline"
  region    = var.region
  schedule  = var.cron_schedule
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project}/locations/${var.region}/jobs/${var.pipeline_job_id}:run"

    oauth_token {
      service_account_email = var.scheduler_email
    }
  }
}
