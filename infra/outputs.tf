output "webhook_url" {
  description = "Cloud Run webhook URL — set as Telegram webhook"
  value       = module.cloud_run.webhook_url
}

output "db_connection_name" {
  description = "Cloud SQL connection name for Cloud SQL Auth Proxy"
  value       = module.cloud_sql.connection_name
}

output "database_url" {
  description = "DATABASE_URL secret value — store in Secret Manager"
  value       = module.cloud_sql.database_url
  sensitive   = true
}

output "artifact_registry_url" {
  description = "Docker registry URL"
  value       = module.artifact_registry.registry_url
}

output "workload_identity_provider" {
  description = "WIF provider — set as GCP_WORKLOAD_IDENTITY_PROVIDER in GitHub repo vars"
  value       = module.service_accounts.workload_identity_provider
}

output "deploy_sa_email" {
  description = "Deploy SA email — set as GCP_DEPLOY_SERVICE_ACCOUNT in GitHub repo vars"
  value       = module.service_accounts.deploy_email
}
