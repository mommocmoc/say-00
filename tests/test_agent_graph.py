"""Tests that the ADK 2.0 workflow graph honours its declared edges.

These exercise execute_say_pipeline end to end through adk_runner, with
the service layer stubbed so no Gemini call is made. The point is not
just the returned payload but which nodes the graph actually visited:
if the pipeline ever regresses to calling the node functions directly,
the routing assertions here still hold, but a graph that stops
dispatching would surface as a missing or extra transform call.
"""

import pytest

from backend import agent
from backend.agent import TransformResponse
from backend.agent import execute_say_pipeline

_FAKE_IMAGE = 'data:image/png;base64,iVBORw0KGgo='
_FAKE_RESULT = 'data:image/jpeg;base64,ZmFrZQ=='


@pytest.fixture
def transform_calls(monkeypatch):
    """Stubs the Gemini transform node and records its invocations."""
    calls = []

    def _fake_transform(image_base64, target_keyword):
        calls.append(target_keyword)
        return {
            'success': True,
            'transformed_image': _FAKE_RESULT,
            'description': f'stubbed transform for {target_keyword}',
        }

    monkeypatch.setattr(agent, 'transform_subject_image', _fake_transform)
    return calls


def _stub_guardrail(monkeypatch, *, is_safe):
    monkeypatch.setattr(
        agent,
        'check_keyword_safety',
        lambda keyword: {
            'is_safe': is_safe,
            'reason': 'stubbed guardrail verdict',
        },
    )


async def test_safe_route_reaches_transform_node(monkeypatch,
                                                 transform_calls):
    """A safe keyword follows the 'safe' edge into the transform node."""
    _stub_guardrail(monkeypatch, is_safe=True)

    result = await execute_say_pipeline(
        image_b64=_FAKE_IMAGE, target_keyword='치즈'
    )

    assert isinstance(result, TransformResponse)
    assert result.is_safe is True
    assert result.success is True
    assert result.transformed_image == _FAKE_RESULT
    assert transform_calls == ['치즈']


async def test_blocked_route_skips_transform_node(monkeypatch,
                                                  transform_calls):
    """An unsafe keyword takes the 'blocked' edge to the formatter.

    The transform node must never run, otherwise the guardrail would be
    paying for a Gemini call on content it already rejected.
    """
    _stub_guardrail(monkeypatch, is_safe=False)

    result = await execute_say_pipeline(
        image_b64=_FAKE_IMAGE, target_keyword='씨발'
    )

    assert isinstance(result, TransformResponse)
    assert result.is_safe is False
    assert result.success is False
    assert result.transformed_image is None
    assert transform_calls == []


async def test_keyword_survives_the_round_trip(monkeypatch,
                                               transform_calls):
    """Input reaches the graph intact through JSON schema validation."""
    _stub_guardrail(monkeypatch, is_safe=True)

    result = await execute_say_pipeline(
        image_b64=_FAKE_IMAGE, target_keyword='솜사탕'
    )

    assert result.target_keyword == '솜사탕'
    assert result.original_image == _FAKE_IMAGE
