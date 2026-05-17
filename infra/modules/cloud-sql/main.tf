variable "project" {}
variable "region" {}
variable "name" {}
variable "tier" { default = "db-g1-small" }

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_sql_database_instance" "main" {
  project          = var.project
  name             = var.name
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier    = var.tier
    edition = "ENTERPRISE"

    ip_configuration {
      ipv4_enabled = true  # Cloud SQL Auth Proxy handles auth; public IP needed for proxy
    }

    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "db" {
  project  = var.project
  name     = "social_assistant"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  project  = var.project
  name     = "social"
  instance = google_sql_database_instance.main.name
  password = random_password.db.result
}

output "connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "db_password" {
  value     = random_password.db.result
  sensitive = true
}

output "database_url" {
  value     = "postgresql://social:${random_password.db.result}@/social_assistant?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
  sensitive = true
}
