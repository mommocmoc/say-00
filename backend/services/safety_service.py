"""Safety and Moderation Service for Say "00" Cam.

Evaluates target keywords for inappropriate, harmful, adult, hate speech,
profanity, or curse words using a comprehensive 4-category offline
dataset and Gemini LLM.
"""

import json
import os
from typing import Set
from dotenv import load_dotenv

# Ensure fresh environment variables from .env
load_dotenv(override=True)

# Global dataset profanity set initialization
INAPPROPRIATE_SET: Set[str] = set()

# All 4 safety dataset categories loaded into the blocklist.
SAFETY_CATEGORY_KEYS = (
    "profanity_and_curse",
    "adult_and_explicit",
    "violence_and_death",
    "illegal_and_weapons",
)


def load_inappropriate_dataset():
    """Loads all 4 categories (Profanity, Adult, Violence, Illegal)."""
    global INAPPROPRIATE_SET
    if INAPPROPRIATE_SET:
        return INAPPROPRIATE_SET

    dataset_path = os.path.join(
        os.path.dirname(__file__), "profanity_words.json"
    )
    words = set()

    if os.path.exists(dataset_path):
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Load all 4 safety categories
                for category_key in SAFETY_CATEGORY_KEYS:
                    for word in data.get(category_key, []):
                        words.add(word.strip().lower())
        except Exception as e:
            print(f"[Warning] Failed to load inappropriate dataset: {e}")

    # Fallback list covering all 4 categories if JSON load fails
    fallback_list = [
        # 1. Profanity
        "씨발", "시발", "존나", "개새끼", "병신", "지랄", "꺼져", "미친", "좆",
        "fuck", "shit", "bitch", "asshole", "bastard", "crap", "dick", "pussy",
        # 2. Adult / Nudity
        "나체", "누드", "음란", "노출", "성인", "19금", "야동", "섹스", "포르노", "성기", "변태",
        "nude", "naked", "nsfw", "sex", "porn", "erotic", "explicit",
        # 3. Death / Violence
        "시체", "시신", "살인", "폭력", "고문", "유혈", "피범벅", "살해", "자살", "테러",
        "corpse", "dead body", "suicide", "torture", "gore", "mutilation",
        # 4. Illegal / Drugs / Weapons
        "마약", "권총", "칼부림", "폭탄", "도박", "drug", "weapon", "gun", "bomb"
    ]
    for w in fallback_list:
        words.add(w)

    INAPPROPRIATE_SET = words
    return INAPPROPRIATE_SET


# Initialize dataset on module load
load_inappropriate_dataset()


def check_keyword_safety(keyword: str) -> dict:
    """Analyze if the target subject keyword is safe.

    Args:
        keyword: Subject type spoken by user (e.g. 'Cheese', '시금치').

    Returns:
        dict: {'is_safe': bool, 'reason': str}
    """
    load_dotenv(override=True)
    clean_keyword = keyword.strip().lower()

    if not clean_keyword:
        return {'is_safe': False, 'reason': '피사체 키워드가 비어 있습니다.'}

    # 1. Fast blocklist substring matching across all 4 categories
    #    (Profanity, Adult, Violence, Illegal).
    bad_word_set = load_inappropriate_dataset()
    for bad_word in bad_word_set:
        if bad_word and bad_word in clean_keyword:
            return {
                'is_safe': False,
                'reason': (
                    f"'{keyword}'은(는) 욕설, 성인/유해, 폭력 또는 부적절한 단어로"
                    ' 판단되어 차단되었습니다.'
                ),
            }

    # 2. Gemini LLM context check for edge cases, when an API key is set.
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = (
                'You are a safety moderator for an image transformation'
                f" app.\nEvaluate if the subject keyword '{keyword}' is"
                ' safe.\nRULES:\n- Common foods, objects, materials,'
                ' animals, toys, furniture'
                ' (e.g., 치즈, 스톤, 캔디, 솜사탕, 시금치, 우주선, 신발) are 100% SAFE.\n-'
                ' DO NOT over-analyze or invent loose associations.\n- MUST'
                ' mark UNSAFE (is_safe: false) if the word contains ANY'
                ' profanity, curse words, swear words, explicit adult'
                ' content, nudity, violence, corpses, blood,'
                ' or illegal drugs/weapons in ANY language.\nRespond ONLY'
                ' in JSON: {"is_safe": true/false, "reason": "explanation'
                ' in Korean"}'
            )
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt,
                config={'response_mime_type': 'application/json'},
            )
            res_data = json.loads(response.text)
            is_safe_val = bool(res_data.get('is_safe', True))
            reason_val = (
                res_data.get('reason', '안전한 키워드입니다.')
                if is_safe_val
                else res_data.get('reason', '부적절하거나 유해한 단어로 차단되었습니다.')
            )
            return {'is_safe': is_safe_val, 'reason': reason_val}
        except Exception as e:
            print(f'Safety check API call fallback: {e}')

    # 3. No blocklist or LLM match: diverse objects/materials pass.
    return {'is_safe': True, 'reason': '안전한 키워드입니다.'}
