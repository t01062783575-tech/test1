"""API-key authentication and short-lived signed download URLs.

Both secrets come from environment variables only — never a source-code
constant, never a CLI argument (which would land in shell history / process
listings), and neither is ever written to a log line (see server.py, which
logs only "authorized: true/false", not the credential).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

API_KEY_ENV_VAR = "SHORTS_RENDERER_API_KEY"
SIGNING_SECRET_ENV_VAR = "SHORTS_RENDERER_SIGNING_SECRET"

DEFAULT_SIGNED_URL_TTL_SECONDS = 15 * 60


class AuthNotConfigured(RuntimeError):
    """Raised at server startup if no API key is configured — refusing to
    boot an unauthenticated render endpoint rather than silently allowing
    open access."""


def ensure_configured() -> None:
    """Call at server startup: raises AuthNotConfigured rather than letting
    the server boot without an API key (fail fast and loud, not silently
    open)."""
    _get_api_key()


def _get_api_key() -> str:
    key = os.environ.get(API_KEY_ENV_VAR)
    if not key:
        raise AuthNotConfigured(
            f"{API_KEY_ENV_VAR} is not set. Refusing to start: this service never runs "
            "as a public unauthenticated render endpoint. Set it to a long random value."
        )
    return key


def _get_signing_secret() -> str:
    # Falls back to the API key so a minimal setup only needs one secret;
    # operators who want the two rotated independently can set both.
    return os.environ.get(SIGNING_SECRET_ENV_VAR) or _get_api_key()


def check_bearer_token(authorization_header: str | None) -> bool:
    """Constant-time comparison against the configured API key. Returns
    False for anything malformed rather than raising, so callers always get
    a clean 401 instead of a 500 on a missing/odd header."""
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    provided = authorization_header[len("Bearer "):].strip()
    expected = _get_api_key()
    return hmac.compare_digest(provided, expected)


def sign_job_output(job_id: str, ttl_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS) -> tuple[str, int]:
    """Return (signature_hex, expires_at_unix) for a time-limited, job-
    scoped download link. The signature covers the job_id and expiry so a
    link can't be edited to point at a different job or extended."""
    expires_at = int(time.time()) + ttl_seconds
    signature = _sign(job_id, expires_at)
    return signature, expires_at


def verify_signed_output_url(job_id: str, expires_at: str | int, signature: str | None) -> bool:
    if not signature:
        return False
    try:
        expires_at_int = int(expires_at)
    except (TypeError, ValueError):
        return False
    if time.time() > expires_at_int:
        return False
    expected = _sign(job_id, expires_at_int)
    return hmac.compare_digest(signature, expected)


def _sign(job_id: str, expires_at: int) -> str:
    secret = _get_signing_secret()
    message = f"{job_id}:{expires_at}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
