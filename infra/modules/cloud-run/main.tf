variable "project" {}
variable "region" {}
variable "db_connection_name" {}
variable "webhook_sa_email" {}
variable "pipeline_sa_email" {}
variable "artifact_registry" {}

locals {
  # Placeholder image — GitHub Actions overwrites this on first push
  placeholder = "us-docker.pkg.dev/cloudrun/container/hello"

  common_env = [
    { name = "GCP_PROJECT", value = var.project },
    { name = "GCP_REGION",  value = var.region },
  ]

  secret_env = [
    { name = "GITHUB_TOKEN",       secret = "github-token" },
    { name = "TELEGRAM_BOT_TOKEN", secret = "telegram-bot-token" },
    { name = "TELEGRAM_CHAT_ID",   secret = "telegram-chat-id" },
    { name = "BLUESKY_HANDLE",     secret = "bluesky-handle" },
    { name = "BLUESKY_PASSWORD",   secret = "bluesky-password" },
    { name = "DATABASE_URL",       secret = "database-url" },
  ]
}

# ── Webhook Cloud Run Service ─────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "webhook" {
  project             = var.project
  name                = "social-assistant-webhook"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = var.webhook_sa_email

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.db_connection_name]
      }
    }

    containers {
      image = local.placeholder

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      dynamic "env" {
        for_each = local.common_env
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.value.name
          value_source {
            secret_key_ref {
              secret  = env.value.secret
              version = "latest"
            }
          }
        }
      }

      resources {
        limits = { memory = "512Mi", cpu = "1" }
      }
    }
  }

  # GitHub Actions manages the container image
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Allow unauthenticated access (Telegram webhook calls this endpoint)
resource "google_cloud_run_v2_service_iam_member" "webhook_public" {
  project  = var.project
  location = google_cloud_run_v2_service.webhook.location
  name     = google_cloud_run_v2_service.webhook.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Pipeline Cloud Run Job ────────────────────────────────────────────────────

resource "google_cloud_run_v2_job" "pipeline" {
  project             = var.project
  name                = "social-assistant-pipeline"
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = var.pipeline_sa_email

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.db_connection_name]
        }
      }

      containers {
        image = local.placeholder

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }

        dynamic "env" {
          for_each = local.common_env
          content {
            name  = env.value.name
            value = env.value.value
          }
        }

        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.value.name
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = "latest"
              }
            }
          }
        }

        resources {
          limits = { memory = "1Gi", cpu = "1" }
        }
      }

      timeout     = "3600s"
      max_retries = 1
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image]
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "webhook_url" {
  value = google_cloud_run_v2_service.webhook.uri
}

output "pipeline_job_name" {
  value = google_cloud_run_v2_job.pipeline.name
}
