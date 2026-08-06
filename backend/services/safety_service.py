"""Safety and Moderation Service for Say "00" Cam.

Evaluates target keywords for inappropriate, harmful, adult, hate speech,
violence, or dangerous content.
"""

import json
import os
from dotenv import load_dotenv

# Ensure fresh environment variables from .env
load_dotenv(override=True)

# Comprehensive list of disallowed concepts/words for offline filtering
INAPPROPRIATE_KEYWORDS = {
    # 1. Adult / Nudity / Explicit / Sexual
    '나체', '누드', '음란', '노출', '성인', '19금', '야동', '섹스', '포르노',
    '성기', '변태', '성범죄', 'nude', 'naked', 'nsfw', 'sex', 'porn', 'erotic',
    'explicit',
    # 2. Death / Corpse / Violence / Gore / Crime
    '시체', '시신', '살인', '폭력', '고문', '유혈', '피범벅', '살해', '자살',
    '학대', '잔혹', '장기절단', '테러', 'corpse', 'dead body', 'cadaver',
    'suicide', 'torture', 'gore', 'mutilation',
    # 3. Hate speech / Slurs / Harassment
    '혐오', '욕설', '비하', '차별', '패륜', '비방', '왕따', 'hate', 'slur',
    'harassment', 'racist', 'abusive',
    # 4. Illegal / Drugs / Weapons
    '마약', '권총', '칼부림', '폭탄', '도박', 'drug', 'weapon', 'gun', 'bomb',
}


def check_keyword_safety(keyword: str) -> dict:
    """Analyze if the target subject keyword is safe.

    Args:
        keyword: The subject type spoken by user (e.g. 'Cheese', 'Stone')

    Returns:
        dict: {'is_safe': bool, 'reason': str}
    """
    load_dotenv(override=True)
    clean_keyword = keyword.strip().lower()

    if not clean_keyword:
        return {'is_safe': False, 'reason': '피사체 키워드가 비어 있습니다.'}

    # 1. Direct and substring matching against exact guardrail list
    for bad_word in INAPPROPRIATE_KEYWORDS:
        if bad_word in clean_keyword:
            return {
                'is_safe': False,
                'reason': (
                    f"'{keyword}'은(는) 부적절하거나 유해한 피사체 유형으로"
                    ' 판단되어 차단되었습니다.'
                ),
            }

    # 2. Check using Gemini API if key is available
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = (
                'You are a safety moderator for an image transformation'
                f" app.\nEvaluate if the subject keyword '{keyword}' is"
                ' safe.\nRULES:\n- Common foods, objects, materials, animals'
                ' (e.g., 치즈, 스톤, 캔디, 솜사탕, 얼음) are 100% SAFE.\n-'
                ' DO NOT over-analyze or invent loose associations.\n- ONLY'
                ' mark unsafe (is_safe: false) if explicitly adult,'
                ' violence/blood, corpses, or illegal drugs.\nRespond ONLY'
                ' in JSON: {"is_safe": true/false, "reason": "explanation'
                ' in Korean"}'
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={'response_mime_type': 'application/json'},
            )
            res_data = json.loads(response.text)
            is_safe_val = bool(res_data.get('is_safe', True))
            reason_val = (
                res_data.get('reason', '안전한 키워드입니다.')
                if is_safe_val
                else res_data.get('reason', '부적절한 단어입니다.')
            )
            return {'is_safe': is_safe_val, 'reason': reason_val}
        except Exception as e:
            print(f'Safety check API call fallback: {e}')

    return {'is_safe': True, 'reason': '안전한 키워드입니다.'}
