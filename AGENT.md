# Agent Specification & Development Guide (AGENT.md)

[![Google ADK 2.0](https://img.shields.io/badge/Google_ADK-2.0_Graph-6366f1?style=for-the-badge&logo=google)](https://adk.dev)
[![Gemini AI](https://img.shields.io/badge/Gemini_AI-gemini--3.1--flash--lite--image-a855f7?style=for-the-badge&logo=google-gemini)](https://ai.google.dev)
[![Code Style: Google Python](https://img.shields.io/badge/Code_Style-Google_Python-blue?style=for-the-badge&logo=python)](https://google.github.io/styleguide/pyguide.html)

---

## 📌 Overview (프로젝트 개요)

[한글]
**Say "00" Cam**은 사용자가 마이크로 **"Say [피사체 유형]"** (예: *Say "Cheese"*, *Say "Stone"*, *Say "Candy"*)을 외치면, 사진이 찍히고 원본 사진 속 메인 피사체를 사용자가 말한 피사체 형태 및 재질로 자동 변환해 주는 아이폰 카메라 스타일의 음성 AI 포트폴리오 프로젝트입니다.

[English]
**Say "00" Cam** is an iOS-style voice-activated AI camera application powered by Google ADK 2.0 Graph Workflow and Gemini Multimodal AI. When the user speaks a command like **"Say [Subject Type]"** (e.g., *Say "Cheese"*, *Say "Stone"*, *Say "Candy"*), the app snaps a photo and transforms the main subject into the requested material or form using Google ADK 2.0 Graph Workflow and Gemini AI (`gemini-3.1-flash-lite-image`).

---

## 📐 System Architecture & Module Map (시스템 아키텍처 및 모듈 구조)

### 1. Backend Architecture (`backend/`)
- **`backend/agent.py`**: ADK 2.0 Graph Workflow 표준 진입점 (`root_agent = Workflow(...)`)
  - **Node 1**: `safety_guardrail_func` (유해성 사전 필터링 및 차단)
  - **Node 2**: `nanobanana_transform_func` (`gemini-3.1-flash-lite-image` 이미지 변환)
  - **Node 3**: `format_output_func` (응답 페이로드 최종 포맷터)
  - **Edges**: 최신 ADK 2.0 딕셔너리 라우팅 튜플 엣지 사용:
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
- **`backend/main.py`**: FastAPI 웹 서버 (REST API `/api/transform`, `/api/safety-check`, `/api/health` 및 정적 웹사이트 서비스)
- **`backend/services/safety_service.py`**: 2단계 하이브리드 유해성 검증 (`INAPPROPRIATE_KEYWORDS` + `gemini-2.5-flash` 심층 검속)
- **`backend/services/nanobanana_service.py`**: `gemini-3.1-flash-lite-image` 이미지 생성 모델 및 PIL 시각적 렌더링 엔진

### 2. Frontend Architecture (`frontend/`)
- **`frontend/index.html`**: 아이폰 네이티브 카메라 UI (상단 HUD, 카메라 뷰파인더, 이중 링 셔터, Siri 말풍선, 슬라이드업 시트)
- **`frontend/style.css`**: 글래스모피즘 디자인 시스템, 스프링 애니메이션, iOS 시트 모달 스타일
- **`frontend/app.js`**: Web Speech API 실시간 음성 인식, 웹캠 스트림 관리, 셔터 애니메이션, 280px 경량화 갤러리 저장

---

## ⚙️ Critical Development Rules for Coding Agents (에이전트 개발 지침)

1. **ADK 2.0 표준 진입점 유지 (Standard Entrypoint)**:
   - `backend/agent.py` 내의 `root_agent`는 상위 Workflow 인스턴스로 항상 고정되어야 합니다.
   - 불필요하게 구식 `Edge(...)` 또는 `FunctionNode(...)` 클래스를 인스턴스화하지 말고, 명확한 튜플 & 딕셔너리 엣지 구문을 사용합니다.

2. **Gemini AI 모델 사용 규칙 (Gemini Models)**:
   - 이미지 변환에는 항상 `google-genai` 패키지의 `gemini-3.1-flash-lite-image` 모델을 사용합니다.
   - API 키 변경에 유연하게 대응하기 위해 항상 `load_dotenv(override=True)`를 통해 환경 변수를 동적으로 읽습니다.

3. **음성 인식 중복 방지 및 쿨다운 (Debounce & Double-Trigger Prevention)**:
   - `frontend/app.js`에서 음성 인식 처리 시 발화가 완결된 `event.results[i].isFinal`이 `true`인 경우에만 촬영 이벤트를 실행합니다.
   - 캡처 후 2.5초간 쿨다운(Debounce)을 두어 "솜", "솜사", "솜사탕"과 같은 중간 인식 텍스트에 의해 연속 연쇄 촬영이 일어나는 것을 방지합니다.

4. **LocalStorage 용량 안전 관리 (Quota Safety)**:
   - 브라우저 LocalStorage 용량 제한(5MB) 초과를 방지하기 위해 갤러리 히스토리 저장 시 280px 썸네일로 압축하여 저장합니다.

5. **코드 스타일 및 린터 검증 (Code Style & Linting)**:
   - 모든 Python 코드는 Google Python Style Guide (PEP 8)를 엄격히 준수합니다.
   - 백엔드 코드 수정 후에는 반드시 `flake8 backend/`를 실행하여 0 Errors 상태를 확인한 후 작업을 완료합니다.
