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

    # OPTIONAL now. google.auth.default() (used in gateway.py) reads Google's
    # standard GOOGLE_APPLICATION_CREDENTIALS environment variable directly —
    # set THAT to whichever credential file you actually have (a service
    # account key if your org allows creating them, or a local
    # "gcloud auth application-default login" file for local dev). This
    # setting is kept for documentation/reference; nothing in the code
    # requires it to be set anymore.
    service_account_key_path: str | None = None

    session_lifetime_hours: int = 8  # matches the spec doc: sessions expire with the school day

    # The real deployed frontend's URL (e.g. https://portal-frontend-xyz.a.run.app,
    # or the real custom domain once one exists). Used to lock down CORS —
    # tightening this matters more now that this is heading to real Cloud
    # Run deployment, not just local testing.
    frontend_origin: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
