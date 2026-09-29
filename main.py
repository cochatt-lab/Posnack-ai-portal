"""FastAPI app: wires Google login, the security gateway, and role-based access together."""
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .auth import oauth, create_session_token, require_session, SESSION_COOKIE, SESSION_MAX_AGE_SECONDS
from .groups import determine_role_and_grade_band
from .gateway import run_gateway

app = FastAPI(title="Posnack School AI Learning Portal")

# Needed by Authlib to stash OAuth state during the login redirect —
# separate from the pal_session cookie used for actual app sessions.
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the real frontend origin before this goes past a pilot
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/auth/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/api/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email", "")

    if not email.endswith("@" + settings.google_workspace_domain):
        raise HTTPException(403, "External accounts are blocked by default.")

    role, _grade_band = determine_role_and_grade_band(email)
    if not role:
        raise HTTPException(403, "Your account isn't in any authorized AI-access group. Contact IT.")

    session_token = create_session_token(email)
    response = RedirectResponse(url="/")
    response.set_cookie(
        SESSION_COOKIE, session_token, max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True, secure=True, samesite="lax",
    )
    return response


@app.get("/api/me")
async def me(session: dict = Depends(require_session)):
    return session


@app.post("/api/ask")
async def ask(request: Request, session: dict = Depends(require_session)):
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "Empty prompt.")
    result = run_gateway(session["email"], session["role"], session.get("grade_band"), prompt)
    return JSONResponse(result)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
