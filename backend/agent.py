"""ADK 2.0 Workflow Agent for Say "00" Cam.

Standard ADK entrypoint module (agent.py) defining root_agent.
Implements the graph node pipeline:
1. Safety Guardrail Node (Harm / inappropriate word detection)
2. NanoBanana Image Transformation Node (Gemini image generation/editing)
3. Response Formatter Node
"""

from typing import Any, Optional
from dotenv import load_dotenv
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.runners import InMemoryRunner
from google.adk.workflow import Workflow
from pydantic import BaseModel

from backend.services.nanobanana_service import transform_subject_image
from backend.services.safety_service import check_keyword_safety

# Load environment variables from .env
load_dotenv()


class TransformRequest(BaseModel):
    image_b64: str
    target_keyword: str
    client_id: Optional[str] = 'default_user'


class TransformResponse(BaseModel):
    success: bool
    is_safe: bool
    reason: str
    target_keyword: str
    original_image: str
    transformed_image: Optional[str] = None
    remaining_shots: Optional[int] = None


def safety_guardrail_func(node_input: TransformRequest) -> Event:
    """ADK 2.0 Graph Node 1: Safety & Moderation Check."""
    keyword = node_input.target_keyword.strip()
    safety_res = check_keyword_safety(keyword)

    if not safety_res['is_safe']:
        blocked_payload = TransformResponse(
            success=False,
            is_safe=False,
            reason=safety_res['reason'],
            target_keyword=keyword,
            original_image=node_input.image_b64,
            transformed_image=None,
        )
        return Event(output=blocked_payload, route='blocked')

    return Event(output=node_input, route='safe')


def nanobanana_transform_func(node_input: TransformRequest) -> Event:
    """ADK 2.0 Graph Node 2: NanoBanana Image Subject Transformation."""
    transform_res = transform_subject_image(
        image_base64=node_input.image_b64,
        target_keyword=node_input.target_keyword,
    )

    success_payload = TransformResponse(
        success=transform_res['success'],
        is_safe=True,
        reason=transform_res['description'],
        target_keyword=node_input.target_keyword,
        original_image=node_input.image_b64,
        transformed_image=transform_res['transformed_image'],
    )
    return Event(output=success_payload, route='done')


def format_output_func(node_input: Any) -> TransformResponse:
    """ADK 2.0 Graph Node 3: Final Output Formatter."""
    if isinstance(node_input, TransformResponse):
        return node_input
    if isinstance(node_input, dict):
        return TransformResponse(**node_input)
    return node_input


# Modern ADK 2.0 routed dictionary tuple edges (auto-wrapped functions)
edges = [
    ('START', safety_guardrail_func),
    (safety_guardrail_func, {
        'safe': nanobanana_transform_func,
        'blocked': format_output_func,
    }),
    (nanobanana_transform_func, format_output_func),
]

# Standard ADK 2.0 root agent entrypoint
root_agent = Workflow(
    name='say_subject_transformer',
    description=(
        'Transforms photo main subject into requested material type after'
        ' passing safety moderation.'
    ),
    input_schema=TransformRequest,
    output_schema=TransformResponse,
    edges=edges,
)

# Initialize ADK App & Runner
adk_app = App(name='say_app', root_agent=root_agent)
adk_runner = InMemoryRunner(app=adk_app)


async def execute_say_pipeline(
    image_b64: str, target_keyword: str
) -> TransformResponse:
    """Executes the ADK 2.0 workflow pipeline for the given input."""
    req = TransformRequest(image_b64=image_b64, target_keyword=target_keyword)

    # Run Node 1: Safety Guardrail
    safety_event = safety_guardrail_func(req)
    route = safety_event.actions.route if safety_event.actions else None

    if route == 'blocked':
        return format_output_func(safety_event.output)

    # Run Node 2: NanoBanana Image Transformation
    transform_event = nanobanana_transform_func(req)
    return format_output_func(transform_event.output)
