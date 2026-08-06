"""Backward compatibility module linking to standard ADK backend/agent.py."""

from backend.agent import execute_say_pipeline
from backend.agent import root_agent as say_workflow
from backend.agent import TransformRequest
from backend.agent import TransformResponse

__all__ = [
    'say_workflow',
    'execute_say_pipeline',
    'TransformRequest',
    'TransformResponse',
]
