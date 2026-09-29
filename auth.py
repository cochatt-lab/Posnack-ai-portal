"""
Google Workspace login (OAuth2/OIDC) + session handling.

Sessions expire after SESSION_LIFETIME_HOURS (8, matching the school
day) — but per the spec doc, that's not the only check: group
membership gets RE-VERIFIED on every session refresh, not only at
initial login. If someone's removed from an authorized Google Group,
this is what actually cuts off their access at the next refresh, rather
than letting it persist for the rest of an active session.
"""
import time
from authlib.integrations.starlette_client import OAuth
from fastapi import Request, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .config import settings
from .groups import determine_role_and_grade_band

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

_signer = URLSafeTimedSerializer(settings.session_secret)
SESSION_COOKIE = "pal_session"
SESSION_MAX_AGE_SECONDS = settings.session_lifetime_hours * 3600


def create_session_token(email: str) -> str:
    # Deliberately does NOT bake role/grade_band into the token long-term —
    # those get looked up fresh on every request via require_session()
    # below, which is the whole point of "re-check on every refresh."
    return _signer.dumps({"email": email, "issued_at": time.time()})


def read_session_token(token: str) -> dict:
    try:
        return _signer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except SignatureExpired:
        raise HTTPException(401, "Session expired — please sign in again.")
    except BadSignature:
        raise HTTPException(401, "Invalid session.")


def require_session(request: Request) -> dict:
    """
    FastAPI dependency: validates the session cookie AND re-checks the
    user's CURRENT Google Group membership against Workspace — never
    trusting a cached role. This is what makes a mid-session group
    removal actually take effect, per the doc's spec.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in.")
    session = read_session_token(token)

    email = session["email"]
    if not email.endswith("@" + settings.google_workspace_domain):
        raise HTTPException(403, "External accounts are blocked by default.")

    role, grade_band = determine_role_and_grade_band(email)
    if not role:
        raise HTTPException(403, "Your account isn't in any authorized AI-access group. Contact IT.")

    session["role"] = role
    session["grade_band"] = grade_band
    return session
