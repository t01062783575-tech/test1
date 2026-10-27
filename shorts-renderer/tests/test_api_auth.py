import time

import pytest

from renderer.api import auth


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv(auth.API_KEY_ENV_VAR, "test-secret-key-123")
    monkeypatch.delenv(auth.SIGNING_SECRET_ENV_VAR, raising=False)
    yield


def test_valid_bearer_token_accepted():
    assert auth.check_bearer_token("Bearer test-secret-key-123") is True


def test_wrong_bearer_token_rejected():
    assert auth.check_bearer_token("Bearer wrong-key") is False


def test_missing_header_rejected():
    assert auth.check_bearer_token(None) is False


def test_malformed_header_rejected():
    assert auth.check_bearer_token("test-secret-key-123") is False  # missing "Bearer " prefix
    assert auth.check_bearer_token("Basic dXNlcjpwYXNz") is False


def test_ensure_configured_raises_when_unset(monkeypatch):
    monkeypatch.delenv(auth.API_KEY_ENV_VAR, raising=False)
    with pytest.raises(auth.AuthNotConfigured):
        auth.ensure_configured()


def test_signed_url_round_trip():
    sig, expires_at = auth.sign_job_output("job-123", ttl_seconds=60)
    assert auth.verify_signed_output_url("job-123", expires_at, sig) is True


def test_signed_url_rejects_wrong_job_id():
    sig, expires_at = auth.sign_job_output("job-123", ttl_seconds=60)
    assert auth.verify_signed_output_url("job-456", expires_at, sig) is False


def test_signed_url_rejects_tampered_expiry():
    sig, expires_at = auth.sign_job_output("job-123", ttl_seconds=60)
    assert auth.verify_signed_output_url("job-123", expires_at + 1000, sig) is False


def test_signed_url_rejects_expired():
    sig, _ = auth.sign_job_output("job-123", ttl_seconds=-1)  # already expired
    assert auth.verify_signed_output_url("job-123", int(time.time()) - 1, sig) is False


def test_signed_url_rejects_garbage_signature():
    _, expires_at = auth.sign_job_output("job-123", ttl_seconds=60)
    assert auth.verify_signed_output_url("job-123", expires_at, "not-a-real-signature") is False


def test_signed_url_rejects_missing_signature():
    assert auth.verify_signed_output_url("job-123", int(time.time()) + 60, None) is False
