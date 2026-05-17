variable "project" {}
variable "region" {}
variable "repo_id" {}

resource "google_artifact_registry_repository" "images" {
  project       = var.project
  location      = var.region
  repository_id = var.repo_id
  format        = "DOCKER"
  description   = "Social Assistant Docker images"
}

output "repo_id" {
  value = google_artifact_registry_repository.images.repository_id
}

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project}/${var.repo_id}"
}
