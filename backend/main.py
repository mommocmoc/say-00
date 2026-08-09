"""FastAPI Web Server for Say "00" Cam.

Serves the REST API endpoints and static frontend web UI.
Loads environment variables from .env file automatically.
Integrates Firebase Firestore Quota management & Storage uploads.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent import execute_say_pipeline, TransformRequest, TransformResponse
from backend.services.safety_service import check_keyword_safety
from backend.services.firebase_service import (
    get_or_create_user_quota,
    check_and_consume_quota,
    reset_user_quota,
    handle_google_login,
    upload_base64_to_storage,
    save_transform_record,
    get_user_history,
)

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title='Say "00" Cam API',
    description='ADK 2.0 Graph powered image main subject transformer based on voice commands.',
    version='1.1.0',
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
    has_firebase_cred = bool(
        os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY') or
        os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')
    )
    return {
        'status': 'ok',
        'app': 'Say "00" Cam ADK 2.0 Transformer',
        'gemini_api_key_configured': has_gemini_key,
        'firebase_configured': has_firebase_cred,
    }


@app.get('/api/user/quota')
async def get_user_quota_endpoint(client_id: str = Query(..., description='Client UUID or anonymous ID')):
    """Gets remaining free and paid shot quota for the client."""
    quota = get_or_create_user_quota(client_id)
    return quota


class GoogleLoginPayload(BaseModel):
    google_uid: str
    email: str
    name: str
    anon_client_id: Optional[str] = None


@app.post('/api/user/google-login')
async def google_login_endpoint(payload: GoogleLoginPayload):
    """Upgrades user to Google account and grants 10 total free shots."""
    quota = handle_google_login(
        google_uid=payload.google_uid,
        email=payload.email,
        name=payload.name,
        anon_client_id=payload.anon_client_id
    )
    return {
        'status': 'success',
        'user_id': f'google_{payload.google_uid}',
        'quota': quota,
    }


@app.get('/api/history')
async def get_user_history_endpoint(client_id: str = Query(...), limit: int = Query(20, le=50)):
    """Retrieves user's recent transformation records from Firestore."""
    history = get_user_history(client_id=client_id, limit=limit)
    return {'client_id': client_id, 'history': history}


class AdminResetPayload(BaseModel):
    client_id: str
    new_shots: Optional[int] = 10


@app.post('/api/admin/reset-quota')
async def admin_reset_quota_endpoint(
    payload: AdminResetPayload,
    admin_secret: Optional[str] = Header(None, alias='X-Admin-Secret')
):
    """Admin-only endpoint to reset user shot quota securely."""
    expected_secret = os.environ.get('ADMIN_SECRET_KEY', 'say_cam_admin_secret_key_2026')
    if not admin_secret or admin_secret != expected_secret:
        raise HTTPException(status_code=401, detail='Invalid or missing Admin Secret Key.')

    success = reset_user_quota(payload.client_id, payload.new_shots or 10)
    if not success:
        raise HTTPException(status_code=500, detail='Failed to reset quota in Firestore.')

    return {
        'status': 'success',
        'client_id': payload.client_id,
        'new_shots': payload.new_shots or 10,
        'message': f'Successfully reset quota for {payload.client_id}'
    }


@app.post('/api/safety-check')
async def safety_check_endpoint(payload: SafetyCheckPayload):
    """Pre-evaluates keyword safety before image processing."""
    res = check_keyword_safety(payload.keyword)
    return res


@app.post('/api/transform', response_model=TransformResponse)
async def transform_endpoint(payload: TransformRequest):
    """Processes image subject transformation through ADK 2.0 Workflow with quota control."""
    if not payload.image_b64 or not payload.target_keyword:
        raise HTTPException(
            status_code=400,
            detail='image_b64 and target_keyword are required.',
        )

    client_id = payload.client_id or 'default_user'

    # Check and consume quota (10 free shots default)
    quota_ok, remaining_shots, msg = check_and_consume_quota(client_id)
    if not quota_ok:
        raise HTTPException(
            status_code=402,
            detail='무료 촬영 횟수(10회)를 모두 소진하였습니다. 레몬스퀴지 결제로 추가 촬영권을 충전해 주세요.',
        )

    # Execute ADK 2.0 Pipeline
    result = await execute_say_pipeline(
        image_b64=payload.image_b64,
        target_keyword=payload.target_keyword,
    )

    # If transformation succeeded and safe, process Firebase Storage & Firestore saving
    if result.is_safe and result.success and result.transformed_image:
        # Try uploading to Firebase Storage for static HTTPS URL
        orig_storage_url = upload_base64_to_storage(payload.image_b64, prefix="orig")
        trans_storage_url = upload_base64_to_storage(result.transformed_image, prefix="trans")

        # Save record to Firestore
        save_transform_record(client_id, {
            'target_keyword': result.target_keyword,
            'original_image': orig_storage_url or result.original_image,
            'transformed_image': trans_storage_url or result.transformed_image,
            'reason': result.reason,
        })

        if orig_storage_url:
            result.original_image = orig_storage_url
        if trans_storage_url:
            result.transformed_image = trans_storage_url

    result.remaining_shots = remaining_shots
    return result


# Serve static web frontend
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'frontend'
)
if os.path.exists(frontend_dir):
    app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')
