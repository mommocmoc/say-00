"""Firebase Storage & Firestore Database Service for Say "00" Cam.

Handles:
- User quota management (10 free shots default)
- Image file uploads to Firebase Storage (PNG/JPEG static HTTPS URLs)
- Transformation history storage and retrieval via Firestore NoSQL DB
"""

import base64
import io
import os
import time
import uuid
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage

load_dotenv()

# Global firebase app and clients initialization
_firebase_app = None
_db = None
_bucket = None


def init_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    global _firebase_app, _db, _bucket

    if _firebase_app:
        return True

    cred_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')
    cred_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET')

    try:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        elif cred_json:
            import json
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Try initializing with default credentials
            cred = credentials.ApplicationDefault()

        options = {}
        if bucket_name:
            options['storageBucket'] = bucket_name

        _firebase_app = firebase_admin.initialize_app(cred, options)
        _db = firestore.client()

        if bucket_name:
            _bucket = storage.bucket()

        print("Firebase Admin SDK successfully initialized.")
        return True
    except Exception as e:
        print(f"[Warning] Firebase initialization alert: {e}")
        return False


def get_db():
    """Gets Firestore database client."""
    init_firebase()
    return _db


def get_storage_bucket():
    """Gets Firebase Storage bucket client."""
    init_firebase()
    return _bucket


def reset_user_quota(client_id: str, new_shots: int = 10) -> bool:
    """Admin function to reset user free shots in Firestore."""
    db = get_db()
    if not db:
        return False

    try:
        user_ref = db.collection("users").document(client_id)
        user_ref.set({
            "free_shots": new_shots,
            "paid_shots": 0,
            "updated_at": time.time(),
        }, merge=True)
        return True
    except Exception as e:
        print(f"Error resetting user quota: {e}")
        return False


def get_or_create_user_quota(client_id: str) -> Dict[str, Any]:
    """Gets user remaining shots or initializes default shots (3 for guest, 10 for logged-in Google users)."""
    db = get_db()
    is_google_user = client_id.startswith("google_") or "@" in client_id
    default_shots = 10 if is_google_user else 3

    if not db:
        return {
            "free_shots": default_shots,
            "paid_shots": 0,
            "total_remaining": default_shots,
            "is_google_user": is_google_user,
            "user_type": "google" if is_google_user else "guest",
        }

    user_ref = db.collection("users").document(client_id)
    doc = user_ref.get()

    if not doc.exists:
        default_quota = {
            "free_shots": default_shots,
            "paid_shots": 0,
            "is_google_user": is_google_user,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        user_ref.set(default_quota)
        return {
            "free_shots": default_shots,
            "paid_shots": 0,
            "total_remaining": default_shots,
            "is_google_user": is_google_user,
            "user_type": "google" if is_google_user else "guest",
        }

    data = doc.to_dict() or {}
    free_shots = data.get("free_shots", 0)
    paid_shots = data.get("paid_shots", 0)
    return {
        "free_shots": free_shots,
        "paid_shots": paid_shots,
        "total_remaining": free_shots + paid_shots,
        "is_google_user": data.get("is_google_user", is_google_user),
        "user_type": "google" if is_google_user else "guest",
    }


def handle_google_login(google_uid: str, email: str, name: str, anon_client_id: Optional[str] = None) -> Dict[str, Any]:
    """Upgrades user to Google account and grants 10 total free shots."""
    db = get_db()
    user_doc_id = f"google_{google_uid}"

    if not db:
        return {"free_shots": 10, "paid_shots": 0, "total_remaining": 10, "is_google_user": True}

    try:
        user_ref = db.collection("users").document(user_doc_id)
        doc = user_ref.get()

        if not doc.exists:
            # Grant 10 free shots upon initial Google Login
            user_ref.set({
                "google_uid": google_uid,
                "email": email,
                "name": name,
                "free_shots": 10,
                "paid_shots": 0,
                "is_google_user": True,
                "created_at": time.time(),
                "updated_at": time.time(),
            })
            total_shots = 10
        else:
            data = doc.to_dict() or {}
            free_shots = data.get("free_shots", 0)
            paid_shots = data.get("paid_shots", 0)
            total_shots = free_shots + paid_shots

        # Migrate history from anonymous client_id if provided
        if anon_client_id and anon_client_id != user_doc_id:
            try:
                records = db.collection("transform_history").where("client_id", "==", anon_client_id).stream()
                for r in records:
                    r.reference.update({"client_id": user_doc_id})
            except Exception as e:
                print(f"Error migrating history: {e}")

        return get_or_create_user_quota(user_doc_id)
    except Exception as e:
        print(f"Error handling Google login: {e}")
        return {"free_shots": 10, "paid_shots": 0, "total_remaining": 10, "is_google_user": True}


def check_and_consume_quota(client_id: str) -> Tuple[bool, int, str]:
    """Checks if user has remaining quota and consumes 1 shot."""
    db = get_db()
    is_google_user = client_id.startswith("google_") or "@" in client_id
    default_shots = 10 if is_google_user else 3

    if not db:
        return True, 999, "Quota OK (Firebase Uninitialized)"

    user_ref = db.collection("users").document(client_id)

    try:
        doc = user_ref.get()
        if not doc.exists:
            free_shots = default_shots
            paid_shots = 0
            user_ref.set({
                "free_shots": free_shots,
                "paid_shots": paid_shots,
                "is_google_user": is_google_user,
                "created_at": time.time(),
                "updated_at": time.time(),
            })
        else:
            data = doc.to_dict() or {}
            free_shots = data.get("free_shots", 0)
            paid_shots = data.get("paid_shots", 0)

        if free_shots > 0:
            free_shots -= 1
        elif paid_shots > 0:
            paid_shots -= 1
        else:
            return False, 0, "QUOTA_EXHAUSTED"

        user_ref.update({
            "free_shots": free_shots,
            "paid_shots": paid_shots,
            "updated_at": time.time(),
        })

        return True, free_shots + paid_shots, "SUCCESS"
    except Exception as e:
        print(f"Error consuming quota: {e}")
        quota_info = get_or_create_user_quota(client_id)
        if quota_info["total_remaining"] > 0:
            return True, quota_info["total_remaining"] - 1, "SUCCESS"
        return False, 0, "QUOTA_EXHAUSTED"


def upload_base64_to_storage(image_b64: str, prefix: str = "img") -> Optional[str]:
    """Uploads Base64 image to Firebase Storage and returns public HTTPS URL."""
    bucket = get_storage_bucket()
    if not bucket:
        return None

    try:
        clean_b64 = image_b64
        mime_type = "image/jpeg"
        ext = "jpg"

        if "," in image_b64:
            header, clean_b64 = image_b64.split(",", 1)
            if "png" in header:
                mime_type = "image/png"
                ext = "png"

        image_bytes = base64.b64decode(clean_b64)
        filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
        blob = bucket.blob(f"say_cam_uploads/{filename}")

        blob.upload_from_string(image_bytes, content_type=mime_type)
        blob.make_public()

        return blob.public_url
    except Exception as e:
        print(f"Error uploading image to Firebase Storage: {e}")
        return None


def save_transform_record(client_id: str, record_data: dict) -> bool:
    """Saves transformation history record to Firestore database."""
    db = get_db()
    if not db:
        return False

    try:
        record_id = uuid.uuid4().hex
        data_to_save = {
            "record_id": record_id,
            "client_id": client_id,
            "target_keyword": record_data.get("target_keyword", ""),
            "original_image": record_data.get("original_image", ""),
            "transformed_image": record_data.get("transformed_image", ""),
            "reason": record_data.get("reason", ""),
            "timestamp": time.time(),
        }
        db.collection("transform_history").document(record_id).set(data_to_save)
        return True
    except Exception as e:
        print(f"Error saving transform record: {e}")
        return False


def get_user_history(client_id: str, limit: int = 20) -> List[dict]:
    """Retrieves user's recent transformation records from Firestore."""
    db = get_db()
    if not db:
        return []

    try:
        docs = (
            db.collection("transform_history")
            .where("client_id", "==", client_id)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        history = []
        for doc in docs:
            d = doc.to_dict()
            history.append(d)
        return history
    except Exception as e:
        print(f"Error querying user history: {e}")
        return []
