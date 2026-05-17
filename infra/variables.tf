variable "project" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Environment name (dev / prod)"
  type        = string
}

variable "db_tier" {
  description = "Cloud SQL machine type"
  type        = string
  default     = "db-f1-micro"
}

variable "pipeline_cron" {
  description = "Cron schedule for the pipeline Cloud Run Job"
  type        = string
  default     = "0 8 * * *"
}

variable "github_org" {
  description = "GitHub organisation or user that owns the repo"
  type        = string
  default     = "karma-works"
}

variable "github_repo" {
  description = "GitHub repository name (without org prefix)"
  type        = string
  default     = "social-assistant"
}
