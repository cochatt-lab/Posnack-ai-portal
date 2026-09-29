"""
The AI Security Gateway — the architectural centerpiece of the spec doc.
Every AI request runs through this pipeline, in this exact order (Google
Authentication -> Role Verification -> Grade Verification happen via
require_session() as a FastAPI dependency BEFORE this function is ever
called — this module picks up from "AI Usage Policy" onward):

  AI Usage Policy -> Sensitive Data Check -> Prompt Security Check ->
  AI Gateway -> Gemini -> Response Security Check -> back to the user

HONEST STATUS OF EACH CHECK — don't oversell any of these to anyone at
Posnack without reading this first:
  - Usage policy: a real, working per-user/per-day request counter.
  - Sensitive-data check: a REAL regex-based scan for common PII
    patterns (SSNs, phone numbers, credit-card-shaped numbers, email
    addresses outside the school domain). This catches the obvious
    cases. It is NOT a substitute for a proper DLP (Data Loss
    Prevention) product — false negatives are expected. Treat this as a
    first layer, not a guarantee, before telling anyone this "detects
    PII."
  - Prompt/response security checks: currently a lightweight keyword
    blocklist (jailbreak-style phrasing, requests to bypass
    instructions, requests to write an entire graded assignment
    outright). This is a starting point, not the finished "Prompt
    Security Check" the doc describes — a real implementation likely
    needs a dedicated classifier model, which is a separate, later build.
"""
import re
import time
from fastapi import HTTPException
import requests
import google.auth
import google.auth.transport.requests
from .config import settings

# ─── Usage policy (real) ────────────────────────────────────────────────
_usage_log: dict[str, list[float]] = {}
DAILY_REQUEST_LIMIT = 200  # per user; tune this per the doc's "usage limits" IT control


def check_usage_policy(email: str):
    now = time.time()
    one_day_ago = now - 86400
    _usage_log.setdefault(email, [])
    _usage_log[email] = [t for t in _usage_log[email] if t > one_day_ago]
    if len(_usage_log[email]) >= DAILY_REQUEST_LIMIT:
        raise HTTPException(429, "Daily AI usage limit reached. Contact your teacher or IT if you need more.")
    _usage_log[email].append(now)


# ─── Sensitive data check (real, basic patterns — see file header) ──────
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_PHONE_RE = re.compile(r"\b\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def check_sensitive_data(text: str, school_domain: str) -> list[str]:
    """Returns flagged pattern names found in the text — an empty list means clean."""
    flags = []
    if _SSN_RE.search(text):
        flags.append("possible SSN")
    if _CREDIT_CARD_RE.search(text):
        flags.append("possible credit card number")
    if _PHONE_RE.search(text):
        flags.append("possible phone number")
    for match in _EMAIL_RE.findall(text):
        if not match.lower().endswith("@" + school_domain.lower()):
            flags.append("email address outside the school domain")
            break
    return flags


# ─── Prompt/response security check (basic keyword screen — see header) ─
_BLOCKED_PATTERNS = [
    "ignore previous instructions", "ignore all previous instructions",
    "pretend you are", "act as if you have no restrictions",
    "write my entire essay", "write my whole assignment for me",
]


def check_prompt_security(text: str) -> list[str]:
    lowered = text.lower()
    return [p for p in _BLOCKED_PATTERNS if p in lowered]


# ─── The actual Gemini call ───────────────────────────────────────────────
def _call_gemini(prompt: str) -> str:
    # "global" gets NO region prefix on the hostname; real regions like
    # "us-central1" DO get a "{region}-" prefix — the exact 404 fixed
    # earlier in the Apps Script build if this distinction is missed.
    host = "aiplatform.googleapis.com" if settings.vertex_location == "global" else f"{settings.vertex_location}-aiplatform.googleapis.com"
    url = (
        f"https://{host}/v1/projects/{settings.gcp_project_id}/locations/"
        f"{settings.vertex_location}/publishers/google/models/{settings.gemini_model}:generateContent"
    )
    credentials, _ = google.auth.load_credentials_from_file(
        settings.service_account_key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    credentials.refresh(google.auth.transport.requests.Request())

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(502, f"Gemini call failed ({response.status_code}): {response.text[:300]}")
    body = response.json()
    return body["candidates"][0]["content"]["parts"][0]["text"]


# ─── The full pipeline, in the doc's exact order ─────────────────────────
def run_gateway(email: str, role: str, grade_band: str | None, prompt: str) -> dict:
    check_usage_policy(email)

    sensitive_flags = check_sensitive_data(prompt, settings.google_workspace_domain)
    if sensitive_flags:
        return {
            "blocked": True,
            "stage": "sensitive_data_check",
            "reason": f"Your message may contain: {', '.join(sensitive_flags)}. Please remove personal information and try again.",
        }

    prompt_flags = check_prompt_security(prompt)
    if prompt_flags:
        return {
            "blocked": True,
            "stage": "prompt_security_check",
            "reason": "This request was blocked by the school's AI usage policy.",
        }

    answer = _call_gemini(prompt)

    response_flags = check_prompt_security(answer)  # same basic screen, applied to the model's own output
    if response_flags:
        return {
            "blocked": True,
            "stage": "response_security_check",
            "reason": "The AI's response was blocked by the school's content policy. Try rephrasing your question.",
        }

    return {"blocked": False, "answer": answer}
