# Posnack School AI Learning Portal

This is a **first slice**, not the finished system described in the original
spec doc — it proves the core architecture end to end: Google Workspace
login, role/grade-band determination via Google Groups (re-checked every
session, not just at login), and the full AI Security Gateway pipeline in
the doc's exact order. Individual tools (homework help, lesson plans,
rubrics, question banks, etc.) aren't built yet — they're all just different
prompts sent through this same gateway, easy to add once this foundation is
confirmed working.

## Before any real student data touches this: a FERPA note

Vertex AI/Gemini already has a confirmed FERPA agreement (from the earlier
Apps Script build). **Google Cloud Run is a separate product and does not
automatically inherit that confirmation.** Before this runs with real student
data, get Cloud Run itself explicitly confirmed under Posnack's Google
Workspace for Education agreement — the same rigor applied to every other
vendor/hosting decision in this project, not something to skip just because
it's the same parent company as Vertex AI.

## What's real vs. what's a stub — read this before telling anyone it's done

- **Login, role/grade-band lookup, session expiry + re-check**: fully real.
- **Usage policy (rate limiting)**: fully real, in-memory per-user daily counter.
- **Sensitive-data check**: real regex scanning for SSNs, phone numbers,
  credit-card-shaped numbers, and non-school email addresses. Catches
  obvious cases — not a substitute for a real DLP product.
- **Prompt/response security check**: a basic keyword blocklist, not the
  finished version the doc describes. Likely needs a dedicated classifier
  model eventually.
- **IT/Security admin console** (audit logs, alerts, emergency disable): not
  built yet.
- **Individual AI tools** (lesson plans, rubrics, question banks, etc.): not
  built yet.
- **Google Groups-based role lookup**: needs a real service account key
  file for domain-wide delegation, which the org policy below currently
  blocks creating. Bypassed for now via DEV_FAKE_ROLE. Unresolved until
  either a key-creation exception is granted, or a different delegation
  mechanism replaces it.

## A real blocker hit during setup, worth knowing about

Posnack's Google Cloud org enforces `iam.disableServiceAccountKeyCreation` —
downloadable service account keys can't be created at all. This is
increasingly Google's own security default, not necessarily something IT
specifically configured. It affects two things differently:
- **Gemini calls**: solved. The code uses Application Default Credentials
  (`google.auth.default()`), which works with your own `gcloud` login
  locally, and with Cloud Run's own attached service account identity in
  real deployment — no downloadable key needed either way.
- **Domain-wide delegation for Google Groups**: NOT solved by the above.
  Impersonating a user to call the Admin SDK Directory API genuinely
  requires a real private key — this is a different mechanism than what
  Gemini calls need. This remains blocked until someone with Organization
  Policy Administrator rights grants an exception, or the feature is
  rebuilt around a different delegation approach.

## Setup steps that need a Workspace admin

1. Create the six Google Groups: ai-admins@, ai-teachers@, ai-students-hs@,
   ai-students-ms@, ai-students-es@, ai-pilot@ (all on the school domain),
   each set to Restricted access type.
2. Resolve the service-account-key policy question above for the Groups
   feature specifically (Gemini calls don't need this resolved).
3. Authorize domain-wide delegation once a key exists, scoped to
   `https://www.googleapis.com/auth/admin.directory.group.readonly`.
4. Set IMPERSONATED_ADMIN_EMAIL in `backend/app/groups.py` to a real
   Workspace super-admin's email.

## Local development (unaffected by the Cloud Run decision)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <your-project-id>

cp .env.example .env
# fill in real values: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET,
# GCP_PROJECT_ID, and set DEV_FAKE_ROLE=Teacher to skip the Groups dependency

docker compose up --build backend frontend
# visit http://localhost:3000
```

`docker-compose.override.yml` mounts your local `gcloud` credentials into the
backend container automatically — this only applies locally, and has nothing
to do with how the real Cloud Run deployment authenticates.

## Deploying to Cloud Run

Real deployment target — replaces the on-prem/Caddy/SSH approach from
earlier drafts of this README. `docker-compose.yml` and `Caddyfile` are no
longer part of the deployment path; they're kept only because
`docker-compose.yml` (with the override file) still drives local testing.

One-time setup, before the GitHub Actions workflow can deploy anything:

1. **Enable Artifact Registry** on the GCP project, and create a Docker
   repository named `posnack-ai-portal` in `us-central1` (or update
   `REGION`/`REPO` in `.github/workflows/deploy.yml` to match your choice).
2. **Create a deploy service account** with roles: Cloud Run Admin,
   Artifact Registry Writer, Agent Platform User, and Service Account User.
3. **Set up Workload Identity Federation** (IAM & Admin → Workload Identity
   Federation → Create Pool) trusting GitHub's OIDC tokens, scoped to this
   specific repository. Allow that pool to impersonate the service account
   from step 2. (This sidesteps the key-creation policy entirely — it's
   the "more secure alternative" Google's own error message pointed at
   earlier.)
4. **Store secrets in Secret Manager**: `google-client-id`,
   `google-client-secret`, `session-secret` — the workflow references these
   by name.
5. **Add GitHub repo secrets** (Settings → Secrets and variables → Actions):
   `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`,
   `GCP_SERVICE_ACCOUNT_EMAIL`.
6. **Update the OAuth Client's authorized redirect URI** once the backend's
   real Cloud Run URL is known (it's random until first deployed), adding
   `https://<real-backend-url>/api/auth/callback` alongside the localhost one.
7. **Set FRONTEND_ORIGIN** on the backend Cloud Run service to the real
   frontend URL once known, so CORS isn't left wide open.

After that one-time setup, every push to `main` builds both images, pushes
them to Artifact Registry, and deploys both to Cloud Run automatically.
