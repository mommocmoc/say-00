#!/bin/bash
# ==============================================================================
# Google Cloud Run One-Click Automated Deployment Script for Say "00" Cam
# Fully safe for Public Repositories (Contains ZERO secret values or credentials)
# ==============================================================================

set -e

SERVICE_NAME="say-00"
REGION="asia-northeast1"

echo "🚀 Starting automated deployment for ${SERVICE_NAME} to GCP Cloud Run (${REGION})..."

# 1. Deploy Cloud Run service with GCP Secret Manager environment variable bindings
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest,ADMIN_SECRET_KEY=ADMIN_SECRET_KEY:latest,FIREBASE_SERVICE_ACCOUNT_KEY=FIREBASE_SERVICE_ACCOUNT_KEY:latest"

echo "🎉 Deployment successfully completed!"
echo "💡 You can view your live service URL from the Cloud Run output above."
