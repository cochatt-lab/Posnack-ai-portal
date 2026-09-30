#!/bin/bash
# One-time Cloud Run deployment setup for the Posnack AI Learning Portal.
# Run this a section at a time (not all at once) — it's meant to be read,
# not blindly executed. Requires: gcloud already installed and logged in
# (gcloud auth login), same as the local testing setup.
#
# IMPORTANT: double-check REPO below matches your GitHub repo EXACTLY,
# including capitalization — this is case-sensitive and a mismatch here
# is a common cause of confusing auth failures later.
set -e

PROJECT_ID="project-895964e2-a6ae-420f-813"
REPO="cochatt-lab/Posnack-ai-portal"   # <-- CONFIRM this matches your actual GitHub org/repo name exactly
REGION="us-central1"

gcloud config set project "$PROJECT_ID"

# ── 1. Enable the APIs this all depends on ──────────────────────────────
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com \
  secretmanager.googleapis.com

# ── 2. Create a Docker repository in Artifact Registry ──────────────────
# This is where your built container images will actually live.
gcloud artifacts repositories create posnack-ai-portal \
  --repository-format=docker \
  --location="$REGION" \
  --description="Posnack AI Learning Portal container images"

# ── 3. Create ONE service account used for both deploying AND running ───
gcloud iam service-accounts create portal-deployer \
  --display-name="Posnack AI Portal Deployer"

DEPLOY_SA="portal-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# ── 4. Grant it exactly what it needs — nothing broader ──────────────────
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" --role="roles/aiplatform.user"

# ── 5. Create a Workload Identity Pool + Provider trusting GitHub ────────
# This is what replaces a downloadable key entirely — GitHub proves its
# own identity to Google directly, no key file ever exists.
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# ── 6. Allow ONLY workflows from that exact repo to impersonate the SA ───
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO}"

# ── 7. Print the two values that go into GitHub repo secrets ────────────
echo ""
echo "===== Copy these into GitHub repo secrets ====="
echo "GCP_SERVICE_ACCOUNT_EMAIL:"
echo "  ${DEPLOY_SA}"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER:"
echo "  projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "GCP_PROJECT_ID:"
echo "  ${PROJECT_ID}"
echo "================================================"

# ── 8. Store the real secrets Cloud Run will read at runtime ─────────────
# Replace the placeholder values below with your real Client ID/Secret
# (from the OAuth Client you already created) and a fresh random string
# for the session secret — do NOT reuse your local .env's session secret.
printf '%s' "PASTE_YOUR_GOOGLE_CLIENT_ID_HERE" | gcloud secrets create google-client-id --data-file=-
printf '%s' "PASTE_YOUR_GOOGLE_CLIENT_SECRET_HERE" | gcloud secrets create google-client-secret --data-file=-
printf '%s' "PASTE_A_NEW_RANDOM_LONG_STRING_HERE" | gcloud secrets create session-secret --data-file=-

# Let the deploy/runtime service account actually read these at startup.
for SECRET in google-client-id google-client-secret session-secret; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${DEPLOY_SA}" --role="roles/secretmanager.secretAccessor"
done

echo "Setup complete. Now add the three values printed above as GitHub repo secrets,"
echo "then push to main to trigger the first deployment."
