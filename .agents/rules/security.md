# Security Rules for Say "00" Cam Repository

## 🚨 STRICT SECURITY MANDATES (비밀 키 및 자격 증명 관련 준수 사항)

1. **절대 하드코딩 금지 (NO HARDCODED KEYS)**:
   - 어떠한 상황에서도 `GEMINI_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_KEY`, `ADMIN_SECRET_KEY`, OAuth Secret 등 비밀키 문자열(예: `AIzaSy...`)을 소스 코드(`*.py`, `*.js`, `*.html`, `*.md`)에 **직접 문자열로 작성하여 커밋해서는 안 됩니다.**

2. **GCP Secret Manager 및 `.env` 사용**:
   - 백엔드는 오직 `os.environ.get()` 또는 GCP Secret Manager를 통해 환경 변수로만 보안 비밀값을 전달받아야 합니다.
   - 개발 환경에서는 `.env` 파일(이미 `.gitignore`에 등록됨)을 사용합니다.

3. **Client-Side Firebase Config 안전화**:
   - 클라이언트 사이드(`frontend/app.js`)의 API 키는 백엔드 인증 프록시(`/api/config`)를 통해 동적으로 받아오거나 비우도록 유지합니다.

4. **Git Pre-Commit & Verification**:
   - 코드 작성 후 커밋 전 `grep -r "AIza" .` 명령으로 하드코딩된 API 키가 포함되어 있는지 반드시 자가 검증합니다.
