# Posnack School AI Learning Portal

This is a **first slice**, not the finished system described in the spec doc —
it proves the core architecture end to end: Google Workspace login, role/grade-band
determination via Google Groups (re-checked every session, not just at login),
and the full AI Security Gateway pipeline in the doc's exact order. Individual
tools (homework help, lesson plans, rubrics, question banks, etc.) aren't built
yet — they're all just different prompts sent through this same gateway, easy
to add once this foundation is confirmed working.

## What's real vs. what's a stub — read this before telling anyone it's done

- **Login, role/grade-band lookup, session expiry + re-check**: fully real.
- **Usage policy (rate limiting)**: fully real, in-memory per-user daily counter.
- **Sensitive-data check**: real regex scanning for SSNs, phone numbers,
  credit-card-shaped numbers, and non-school email addresses. This catches
  obvious cases — it is **not** a substitute for a real DLP product, and false
  negatives are expected.
- **Prompt/response security check**: a basic keyword blocklist right now, not
  the finished version the doc describes. A production version likely needs a
  dedicated classifier model — a separate, later build.
- **IT/Security admin console** (audit logs, security alerts, emergency
  disable): not built yet at all.
- **Individual AI tools** (lesson plans, rubrics, question banks, etc.): not
  built yet — see above.

## Setup steps that need a Workspace admin (can't be done from code)

1. Create Google Groups: `ai-admins@`, `ai-teachers@`, `ai-students-hs@`,
   `ai-students-ms@`, `ai-students-es@`, `ai-pilot@` (all on the school domain).
2. Create a GCP service account with the **Agent Platform User** role on the
   project used for Gemini (same project already validated in the earlier
   Apps Script build).
3. Download that service account's JSON key, and authorize **domain-wide
   delegation** for it in the Workspace Admin Console (Security → API
   controls → Domain-wide delegation), scoped to:
   `https://www.googleapis.com/auth/admin.directory.group.readonly`
4. Set `IMPERSONATED_ADMIN_EMAIL` in `backend/app/groups.py` to a real
   Workspace super-admin's email — delegation calls must impersonate an
   actual admin user.
5. Create an OAuth 2.0 Client ID (Web application type) in Google Cloud
   Console, with an authorized redirect URI matching your real domain
   (e.g. `https://ai.posnackschool.org/api/auth/callback`).

## Local setup

```bash
cp .env.example .env
# fill in .env with real values
mkdir -p secrets
# put the service account JSON key at ./secrets/service-account.json
docker compose up --build
```

## Deploying on-prem via GitHub Actions

1. Push this repo to a GitHub repository.
2. On the actual on-prem server: install Docker and Docker Compose, then
   `git clone` this repo once manually to `/opt/posnack-ai-portal`.
3. In GitHub → repo Settings → Secrets and variables → Actions, add:
   `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` (a private key whose matching
   public key is authorized on that server).
4. Every push to `main` now rebuilds and restarts the containers on that
   server automatically.
5. Point `ai.posnackschool.org`'s DNS at that server's IP, and update the
   `Caddyfile` if the domain differs — Caddy handles HTTPS certificates
   automatically once DNS is pointed correctly.
