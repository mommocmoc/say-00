"""Tests for the offline stage of the 2-stage safety guardrail.

Stage 1 is a blocklist lookup that short-circuits before any Gemini
call, so the blocking tests never touch the network regardless of
whether a key is configured.
"""

import pytest

from backend.services.safety_service import SAFETY_CATEGORY_KEYS
from backend.services.safety_service import check_keyword_safety
from backend.services.safety_service import load_inappropriate_dataset


def test_dataset_covers_all_four_categories():
    """The blocklist merges every declared safety category."""
    assert len(SAFETY_CATEGORY_KEYS) == 4
    assert len(load_inappropriate_dataset()) > 500


@pytest.mark.parametrize(
    'keyword',
    [
        '씨발',   # profanity
        '누드',   # adult / nudity
        '시체',   # violence / death
        '마약',   # illegal / drugs
    ],
)
def test_blocklist_rejects_every_category(keyword):
    """One representative term per category must be blocked offline."""
    result = check_keyword_safety(keyword)

    assert result['is_safe'] is False
    assert result['reason']


def test_blocklist_matching_is_case_insensitive():
    assert check_keyword_safety('FUCK')['is_safe'] is False


def test_blank_keyword_is_rejected():
    assert check_keyword_safety('   ')['is_safe'] is False


@pytest.mark.parametrize('keyword', ['치즈', 'Cheese', '솜사탕', '우주선'])
def test_ordinary_subjects_pass(offline_guardrail, keyword):
    """Everyday subjects survive stage 1 and default to safe."""
    assert check_keyword_safety(keyword)['is_safe'] is True
