"""FastAPI Web Server for Say "00" Cam.

Serves the REST API endpoints and static frontend web UI.
Loads environment variables from .env file automatically.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.services.safety_service import check_keyword_safety
from backend.workflow import execute_say_pipeline
from backend.workflow import TransformRequest
from backend.workflow import TransformResponse

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title='Say "00" Cam API',
    description=(
        'ADK 2.0 Graph powered image main subject transformer based on voice'
        ' commands.'
    ),
    version='1.0.0',
)

# Enable CORS for local development and web requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class SafetyCheckPayload(BaseModel):
    keyword: str


@app.get('/api/health')
async def health_check():
    """Returns API health status."""
    has_gemini_key = bool(os.environ.get('GEMINI_API_KEY'))
    return {
        'status': 'ok',
        'app': 'Say "00" Cam ADK 2.0 Transformer',
        'gemini_api_key_configured': has_gemini_key,
    }


@app.post('/api/safety-check')
async def safety_check_endpoint(payload: SafetyCheckPayload):
    """Pre-evaluates keyword safety before image processing."""
    res = check_keyword_safety(payload.keyword)
    return res


@app.post('/api/transform', response_model=TransformResponse)
async def transform_endpoint(payload: TransformRequest):
    """Processes image subject transformation through ADK 2.0 Workflow."""
    if not payload.image_b64 or not payload.target_keyword:
        raise HTTPException(
            status_code=400,
            detail='image_b64 and target_keyword are required.',
        )

    result = await execute_say_pipeline(
        image_b64=payload.image_b64,
        target_keyword=payload.target_keyword,
    )
    return result


# Serve static web frontend
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'frontend'
)
if os.path.exists(frontend_dir):
    app.mount('/', StaticFiles(directory=frontend_dir,
              html=True), name='frontend')
