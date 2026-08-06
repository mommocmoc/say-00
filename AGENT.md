# Agent Specification & Development Guide (AGENT.md)

## 📌 Project Overview
**Say "00" Cam** is an iOS-style voice-activated AI camera application powered by Google ADK 2.0 Graph Workflow and Gemini Multimodal AI.
When the user speaks a command like **"Say [Subject Type]"** (e.g., *Say "Cheese"*, *Say "Stone"*, *Say "Candy"*), the app snaps a photo and transforms the main subject into the requested material or form using Google ADK 2.0 Graph Workflow and Gemini AI (`gemini-3.1-flash-lite-image`).

---

## 📐 System Architecture & Module Map

### 1. Backend Architecture (`backend/`)
- `backend/agent.py`: Standard ADK 2.0 Graph Workflow entrypoint defining `root_agent = Workflow(...)`.
  - **Node 1**: `safety_guardrail_func` (Safety & moderation filtering)
  - **Node 2**: `nanobanana_transform_func` (`gemini-3.1-flash-lite-image` subject generation)
  - **Node 3**: `format_output_func` (Response payload formatter)
  - Uses modern ADK 2.0 dictionary routed tuple edges:
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
- `backend/services/safety_service.py`: 2-stage hybrid safety moderation (`INAPPROPRIATE_KEYWORDS` + `gemini-2.5-flash` context check).
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
