"""
Role and grade-band determination via Google Groups membership — exactly
what the spec doc asked for: group membership determines access, and
it's re-checked on every session refresh, not just at login. This is
deliberately NOT a hardcoded role table (unlike the earlier Apps Script
build's Roles sheet) — removing someone from a group is what actually
cuts off access here.

SETUP THIS NEEDS FROM A WORKSPACE ADMIN — none of this works until these
are done, and none of it can be done from code alone:
  1. Create the Google Groups: ai-admins@, ai-teachers@, ai-students-hs@,
     ai-students-ms@, ai-students-es@, ai-pilot@ (all @ the school domain).
  2. Create a GCP service account, download its JSON key, mount it where
     SERVICE_ACCOUNT_KEY_PATH points.
  3. In the Workspace Admin Console -> Security -> API controls ->
     Domain-wide delegation, authorize that service account's Client ID
     for scope: https://www.googleapis.com/auth/admin.directory.group.readonly
  4. Set IMPERSONATED_ADMIN_EMAIL below to a real Workspace super-admin's
     email — domain-wide delegation calls must impersonate an actual
     admin user; a bare service account can't call this API directly.
"""
from googleapiclient.discovery import build
from google.oauth2 import service_account
from .config import settings
import os

SCOPES = ["https://www.googleapis.com/auth/admin.directory.group.readonly"]

# TODO: set to a real Workspace super-admin's email.
IMPERSONATED_ADMIN_EMAIL = "PASTE_A_REAL_WORKSPACE_ADMIN_EMAIL_HERE"

# DEV MODE: if this env var is set, group lookups are skipped entirely and
# everyone gets this fixed role instead — for testing login + the gateway
# pipeline BEFORE a Workspace admin has created the real groups and
# authorized domain-wide delegation. Unset this before anything resembling
# real use; it makes every signed-in user the same role, with no real
# access control at all.
DEV_FAKE_ROLE = os.environ.get("DEV_FAKE_ROLE")  # e.g. "Teacher"
DEV_FAKE_GRADE_BAND = os.environ.get("DEV_FAKE_GRADE_BAND")  # e.g. "High School", or leave unset

ROLE_GROUPS = {
    "ai-admins@": "Admin",
    "ai-teachers@": "Teacher",
    "ai-students-hs@": "Student",
    "ai-students-ms@": "Student",
    "ai-students-es@": "Student",
}
GRADE_BAND_GROUPS = {
    "ai-students-hs@": "High School",
    "ai-students-ms@": "Middle School",
    "ai-students-es@": "Elementary",
}


def _directory_service():
    creds = service_account.Credentials.from_service_account_file(
        settings.service_account_key_path, scopes=SCOPES
    ).with_subject(IMPERSONATED_ADMIN_EMAIL)
    return build("admin", "directory_v1", credentials=creds, cache_discovery=False)


def get_user_groups(email: str) -> list[str]:
    """Every Google Group email address this user currently belongs to."""
    service = _directory_service()
    result = service.groups().list(userKey=email, domain=settings.google_workspace_domain).execute()
    return [g["email"].lower() for g in result.get("groups", [])]


def determine_role_and_grade_band(email: str) -> tuple[str | None, str | None]:
    """
    Looks up current group membership and maps it to (role, grade_band).
    Returns (None, None) if the user isn't in any recognized group — per
    the doc's "external accounts blocked by default" principle, that
    should deny access, not fall back to a default role.
    """
    if DEV_FAKE_ROLE:
        return DEV_FAKE_ROLE, DEV_FAKE_GRADE_BAND

    groups = get_user_groups(email)
    role = None
    grade_band = None
    for prefix, mapped_role in ROLE_GROUPS.items():
        if any(g.startswith(prefix) for g in groups):
            role = mapped_role
            break
    for prefix, band in GRADE_BAND_GROUPS.items():
        if any(g.startswith(prefix) for g in groups):
            grade_band = band
            break
    return role, grade_band
