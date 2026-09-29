"""
Central place for every value this backend needs from the environment.
Nothing security-relevant has a default on purpose — a missing value
should fail loudly at startup, not silently misbehave in production.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    google_workspace_domain: str  # e.g. "posnackschool.org" — external accounts are rejected against this
    session_secret: str  # a random long string, used to sign session cookies

    # Same GCP project/model already validated end-to-end in the Apps
    # Script PAL platform build. "global" is intentional, not a mistake —
    # newer Gemini 3.x models are frequently global-only, not tied to a
    # specific region like us-central1 (that exact 404 was hit and fixed
    # once already in the Apps Script build).
    gcp_project_id: str
    vertex_location: str = "global"
    gemini_model: str = "gemini-3.1-flash-lite"

    # Path to a Service Account JSON key with (a) the "Agent Platform
    # User" IAM role on the GCP project above, and (b) domain-wide
    # delegation authorized by a Workspace admin for the Admin SDK
    # Directory API's groups.readonly scope — needed to check a user's
    # Google Group membership for role/grade-band determination.
    # Authorizing delegation is a Workspace-admin-level step; it can't be
    # done from this code.
    service_account_key_path: str

    session_lifetime_hours: int = 8  # matches the spec doc: sessions expire with the school day

    class Config:
        env_file = ".env"


settings = Settings()
