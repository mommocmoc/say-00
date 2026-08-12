# Agent Specification & Development Guide (AGENT.md)

[![Google ADK 2.0](https://img.shields.io/badge/Google_ADK-2.0_Graph-6366f1?style=for-the-badge&logo=google)](https://adk.dev)
[![Gemini AI](https://img.shields.io/badge/Gemini_AI-gemini--3.1--flash--lite--image-a855f7?style=for-the-badge&logo=google-gemini)](https://ai.google.dev)
[![Code Style: Google Python](https://img.shields.io/badge/Code_Style-Google_Python-blue?style=for-the-badge&logo=python)](https://google.github.io/styleguide/pyguide.html)

---

## 📌 Overview
**Say "00" Cam** is an iOS-style voice-activated AI camera application powered by Google ADK 2.0 Graph Workflow and Gemini Multimodal AI.
When the user speaks a command like **"Say [Subject Type]"** (e.g., *Say "Cheese"*, *Say "Stone"*, *Say "Candy"*), the app snaps a photo and transforms the main subject into the requested material or form using Google ADK 2.0 Graph Workflow and Gemini AI (`gemini-3.1-flash-lite-image`).

---

## 📐 System Architecture & Module Map

### 1. Backend Architecture (`backend/`)
- `backend/agent.py`: Standard ADK 2.0 Graph Workflow entrypoint defining `root_agent = Workflow(...)`.
  - **Node 1**: `safety_guardrail_func` (Safety & moderation filtering)
  - **Node 2**: `nanobanana_transform_func` (`gemini-3.1-flash-lite-image` subject generation)
  - **Node 3**: `format_output_func` (Response payload formatter)
  - **Edges**: Uses modern ADK 2.0 dictionary routed tuple edges:
    ```python
    edges = [
        ('START', safety_guardrail_func),
        (safety_guardrail_func, {
            'safe': nanobanana_transform_func,
            'blocked': format_output_func
        }),
        (nanobanana_transform_func, format_output_func)
    ]
    ```
- `backend/main.py`: FastAPI web server serving REST API endpoints (`POST /api/transform`, `POST /api/safety-check`, `GET /api/health`) and mounting static web files.
- `backend/services/safety_service.py`: 2-stage hybrid safety moderation (`INAPPROPRIATE_KEYWORDS` + `gemini-3.5-flash-lite` context check).
- `backend/services/nanobanana_service.py`: `gemini-3.1-flash-lite-image` model integration with PIL visual fallback engine.

### 2. Frontend Architecture (`frontend/`)
- `frontend/index.html`: Native iOS Camera UI layout with top HUD (`⚡` Flash, `(?)` About, `🌐` Grid), video feed, double-ring shutter button, floating Siri voice bubble, and slide-up sheet cards.
- `frontend/style.css`: Glassmorphism iOS design system, spring animations, and slide-up sheet modals.
- `frontend/app.js`: Web Speech API continuous recognition, webcam video stream, shutter flash animation, API integration, and quota-safe gallery history.

---

## ⚙️ Critical Development Rules for Coding Agents

1. **ADK 2.0 Standard Entrypoint**:
   - `root_agent` in `backend/agent.py` MUST remain the root Workflow instance.
   - Do NOT import or instantiate legacy `Edge(...)` or `FunctionNode(...)` wrappers unnecessarily; use clean tuple & dictionary edge definitions.
   - Node functions MUST be reached through `adk_runner.run_async()`, never called directly in sequence. Calling them by hand bypasses graph routing and makes the declared `edges` dead code.
   - The runner receives the request as a `types.Content` JSON message; `Workflow.input_schema` validates and parses it. The terminal event output arrives as a plain `dict`, so normalize it via `format_output_func`.

2. **Gemini AI Models**:
   - Always use `gemini-3.1-flash-lite-image` via `google-genai` `generate_content` for image subject transformation.
   - Always load environment variables dynamically using `load_dotenv(override=True)` to ensure fresh API key reads.

3. **Speech Recognition Debounce & Double-Trigger Prevention**:
   - In `frontend/app.js`, ONLY process voice triggers when `event.results[i].isFinal` is `true`.
   - Maintain a 2.5s debounce cooldown after capture to prevent partial phrases (e.g. "솜", "솜사", "솜사탕") from triggering multiple back-to-back shots.

4. **LocalStorage Quota Safety**:
   - When saving history items to LocalStorage, compress transformed images to 280px thumbnails to prevent `QuotaExceededError`.

5. **Code Style & Linting Verification**:
   - All Python code MUST strictly adhere to the Google Python Style Guide.
   - Run `flake8 backend/` after making backend changes to verify zero errors before declaring task completion.

6. **🚨 Zero-Hardcoding & Secret Security Rule**:
   - **NEVER hardcode API keys, secrets, or credential tokens** (e.g. `AIzaSy...`) in any file (`app.js`, `README.md`, `agent.py` etc.).
   - All secrets MUST be injected via `os.environ` or GCP Secret Manager.
   - Before committing, verify zero secret strings using `grep -r "AIza" .`.

---

## 📋 Development Backlog & Roadmap

> **📍 Branch Scope Notice**
> This document describes the **`main`** branch, which is the deployed production
> build serving <https://say-00-cam.cowcowwow.kr>. Monetization and account
> features (Firestore quota, Google Sign-In, payments) are **not** part of `main`
> — they live on the `feature/firebase-quota-mobile-download` branch and are
> listed separately below. The module map in section 1–2 reflects `main` only.

### ✅ Completed & Shipped on `main` (Production)
- [x] **iOS Camera UI & Siri Voice Recognition**: Edge-to-edge camera feed with Web Speech API (`isFinal` speech detection & attached speech slot extraction e.g. "세이치즈", "saycheese").
- [x] **ADK 2.0 Graph & Gemini Multimodal Engine**: Safety guardrail node (Expanded 4-category offline dataset: Profanity, Adult/Nudity, Violence/Death, Illegal/Weapons) & `gemini-3.1-flash-lite-image` subject transformer.
- [x] **ADK 2.0 Runner-Driven Graph Execution**: `execute_say_pipeline` submits the request to `adk_runner.run_async()`, so the declared `Workflow` graph performs node dispatch and edge routing. Each call uses a throwaway session that is deleted afterwards.
- [x] **2-Stage Hybrid Safety Guardrail**: Zero-latency offline blocklist (562 terms) backed by a `gemini-3.5-flash-lite` contextual moderation pass that catches terms the blocklist misses.
- [x] **LocalStorage Quota-Safe History Gallery**: 280px thumbnail compression to stay within the 5MB `localStorage` budget.
- [x] **GCP Cloud Run Deploy Automation**: Created safe `deploy.sh` script with GCP Secret Manager bindings using production `Dockerfile` for `say-00` in `asia-northeast1`.
- [x] **Git Branching Strategy**: Created and pushed feature branch `feature/firebase-quota-mobile-download` to origin to protect `main` branch auto-deployment trigger.

### 🚧 In Progress on `feature/firebase-quota-mobile-download` (Not in `main`)
These are implemented on the feature branch and pending review before merge.
Do NOT assume these modules or endpoints exist when working on `main`.

- [ ] **Mobile Reliable Download & Native Share**: Blob Object URL download & Web Share API (`navigator.share`) for iOS photo album saving.
- [ ] **3-Tier Quota & Auth Architecture**:
  - **Tier 1 (Guest)**: 3-shot free preview (`free_shots: 3`).
  - **Tier 2 (Google Member)**: 1초 Google Login for 7 additional shots (Total 10 free shots).
  - **Tier 3 (Paid Member)**: Lemon Squeezy payment recharge modal ($0.79 / 5 shots).
- [ ] **Firestore & Firebase Storage Integration** (`backend/services/firebase_service.py`): Persistent user quota tracking and public HTTPS storage URLs.
- [ ] **Admin Quota API**: `POST /api/admin/reset-quota` with `X-Admin-Secret` header verification and GCP Secret Manager integration.
- [ ] **Firebase Auth Production SDK**: Firebase Web SDK v10 `GoogleAuthProvider` popup for 1-second Google Sign-In & 7-shot bonus upgrade.

### ⏳ Pending Backlog (Next Steps)
- [ ] **Lemon Squeezy Live Store Integration**: Replace client-side mock modal trigger with official Lemon Squeezy SDK (`LemonSqueezy.Url.Open`) and Webhook (`POST /api/webhook/lemonsqueezy`) handler.
