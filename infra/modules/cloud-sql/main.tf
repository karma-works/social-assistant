variable "project" {}
variable "region" {}
variable "name" {}
variable "tier" { default = "db-f1-micro" }

resource "google_sql_database_instance" "main" {
  name             = var.name
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier = var.tier
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "db" {
  name     = "social_assistant"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "social"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

resource "google_compute_network" "vpc" {
  name                    = "${var.name}-vpc"
  auto_create_subnetworks = false
}

variable "db_password" {
  sensitive = true
  default   = ""
}

output "connection_name" {
  value = google_sql_database_instance.main.connection_name
}
