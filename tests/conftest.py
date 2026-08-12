"""Shared pytest fixtures for Say "00" Cam.

Every test in this suite runs offline. No Gemini call, no network, and
no GEMINI_API_KEY required, so the suite is safe to run in CI.
"""

import pytest

from backend.services import safety_service


@pytest.fixture
def offline_guardrail(monkeypatch):
    """Forces the safety guardrail to skip its Gemini stage.

    check_keyword_safety() calls load_dotenv(override=True) on every
    invocation, which would re-read .env and restore a real key right
    after we delete it. The loader is stubbed out first so that
    deleting the variable actually sticks.
    """
    monkeypatch.setattr(safety_service, 'load_dotenv', lambda **kw: None)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    return safety_service
