#!/usr/bin/env bash
# Run once before `terraform init` to create the GCS state bucket and enable
# the APIs that Terraform itself needs to run.
set -euo pipefail

PROJECT="social-assistant-496611"
REGION="us-central1"
BUCKET="${PROJECT}-tfstate"

echo "==> Enabling core APIs (needed for Terraform to run)..."
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com \
  --project "$PROJECT"

echo "==> Creating Terraform state bucket: gs://$BUCKET"
if ! gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" &>/dev/null; then
  gcloud storage buckets create "gs://$BUCKET" \
    --project "$PROJECT" \
    --location "$REGION" \
    --uniform-bucket-level-access
  gcloud storage buckets update "gs://$BUCKET" --versioning
  echo "    Bucket created."
else
  echo "    Bucket already exists — skipping."
fi

echo ""
echo "==> Bootstrap complete. Next steps:"
echo ""
echo "  cd infra"
echo "  terraform init -backend-config=environments/dev/backend.tf"
echo "  terraform plan  -var-file=environments/dev/terraform.tfvars"
echo "  terraform apply -var-file=environments/dev/terraform.tfvars"
echo ""
echo "  After apply, populate secrets:"
echo "    terraform output -raw database_url | gcloud secrets versions add database-url --data-file=- --project $PROJECT"
echo "    echo -n 'YOUR_GITHUB_TOKEN'       | gcloud secrets versions add github-token --data-file=- --project $PROJECT"
echo "    echo -n 'YOUR_TELEGRAM_BOT_TOKEN' | gcloud secrets versions add telegram-bot-token --data-file=- --project $PROJECT"
echo "    echo -n 'YOUR_TELEGRAM_CHAT_ID'   | gcloud secrets versions add telegram-chat-id --data-file=- --project $PROJECT"
echo "    echo -n 'YOUR_BLUESKY_HANDLE'     | gcloud secrets versions add bluesky-handle --data-file=- --project $PROJECT"
echo "    echo -n 'YOUR_BLUESKY_PASSWORD'   | gcloud secrets versions add bluesky-password --data-file=- --project $PROJECT"
echo ""
echo "  Run DB migrations via Cloud SQL Auth Proxy:"
echo "    cloud-sql-proxy ${PROJECT}:${REGION}:<INSTANCE_NAME> --port 5432 &"
echo "    psql postgresql://social:PASSWORD@localhost:5432/social_assistant -f migrations/001_initial.sql"
echo ""
echo "  Set Telegram webhook (after first GitHub Actions deploy):"
echo "    WEBHOOK_URL=\$(terraform output -raw webhook_url)"
echo "    curl \"https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/setWebhook?url=\${WEBHOOK_URL}/telegram/webhook\""
echo ""
echo "  Add GitHub Actions repo variables:"
echo "    GCP_PROJECT                  = $PROJECT"
echo "    GCP_REGION                   = $REGION"
echo "    GCP_WORKLOAD_IDENTITY_PROVIDER = \$(terraform output -raw workload_identity_provider)"
echo "    GCP_DEPLOY_SERVICE_ACCOUNT   = \$(terraform output -raw deploy_sa_email)"
