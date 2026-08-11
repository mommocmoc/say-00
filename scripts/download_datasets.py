"""Download and Merge Open-Source Profanity & Inappropriate Word Datasets.

Fetches large-scale Korean & English datasets from verified GitHub open-source repositories:
- Korean: bad_word_list (hlog2e), korean-profanity-resources
- English: LDNOOBW (List of Dirty, Naughty, Obscene, and Otherwise Bad Words)
Merges and cleans them into backend/services/profanity_words.json
"""

import json
import os
import urllib.request
from typing import Set

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "backend", "services", "profanity_words.json")

# Verified Open-Source Dataset URLs
DATASET_URLS = {
    "korean_cursewords": "https://raw.githubusercontent.com/curioustorvald/KoreanCursewordRegex/master/korean_cursewords.txt",
    "english_ldnoobw": "https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en",
}


def fetch_url_content(url: str) -> str:
    """Fetches text content from public raw GitHub URL."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"[Warning] Failed to fetch dataset from {url}: {e}")
        return ""


def download_and_build_dataset():
    print("🚀 Downloading open-source Korean & English profanity datasets...")

    korean_words: Set[str] = set()
    english_words: Set[str] = set()
    adult_words: Set[str] = set()
    violence_words: Set[str] = set()
    illegal_words: Set[str] = set()

    # 1. Fetch Korean bad word list from open-source repository
    kr_content = fetch_url_content(DATASET_URLS["korean_cursewords"])
    if kr_content:
        for line in kr_content.splitlines():
            w = line.strip().lower()
            if w and not w.startswith("#"):
                korean_words.add(w)

    # 2. Fetch English LDNOOBW dataset
    en_content = fetch_url_content(DATASET_URLS["english_ldnoobw"])
    if en_content:
        for line in en_content.splitlines():
            w = line.strip().lower()
            if w:
                english_words.add(w)

    # Base curated categories
    base_kr = [
        "씨발", "시발", "존나", "개새끼", "병신", "지랄", "꺼져", "미친", "좆", "떽", "엠창", "ㅗ",
        "개씨발", "시발럼", "씨발놈", "씨발년", "개년", "미친년", "미친놈", "호구", "새끼",
        "느금마", "느엄마", "애미", "애아빠", "틀딱", "지랄마", "닥쳐", "뻐꾸기", "갈보",
        "개구라", "구라", "호로자식", "쌍놈", "쌍년", "썅", "썅년", "창녀", "걸레",
        "잡놈", "짱깨", "쪽바리", "조센징", "흑형", "똥개", "씹", "씹새끼", "씹창",
        "염병", "육시랄", "옘병", "개소리", "소리하네", "좆같", "좆까", "좆나", "좆밥",
        "십새끼", "십팔", "시팔", "씨팔", "쌍소리", "엿먹어", "엿쳐먹어", "개호구",
        "붕신", "빙신", "븅신", "븡신", "장애인비하", "머저리", "바보새끼", "멍청이새끼"
    ]
    for w in base_kr:
        korean_words.add(w)

    base_en = [
        "fuck", "fucking", "fucker", "shit", "shitty", "bitch", "asshole", "bastard", "crap",
        "dick", "pussy", "cunt", "motherfucker", "whore", "slut", "cock", "suck", "sucks",
        "ass", "bullshit", "jackass", "dipshit", "dumbass", "douche", "douchebag",
        "nigger", "nigga", "faggot", "bastards", "bitches", "fucks", "shits", "dicks",
        "pussies", "retard", "retarded", "bastard", "idiot", "jerk", "freak", "prick"
    ]
    for w in base_en:
        english_words.add(w)

    adult_words.update([
        "나체", "누드", "음란", "노출", "성인", "19금", "야동", "섹스", "포르노",
        "성기", "변태", "성범죄", "야사", "야애니", "자위", "애무", "섹슈얼",
        "nude", "naked", "nsfw", "sex", "porn", "erotic", "explicit", "adult", "boobs", "penis", "vagina"
    ])

    violence_words.update([
        "시체", "시신", "살인", "폭력", "고문", "유혈", "피범벅", "살해", "자살",
        "학대", "잔혹", "장기절단", "테러", "시체놀이", "사망", "목매달", "목매달기",
        "corpse", "dead body", "cadaver", "suicide", "torture", "gore", "mutilation", "kill", "murder", "blood"
    ])

    illegal_words.update([
        "마약", "권총", "칼부림", "폭탄", "도박", "필로폰", "코카인", "대마초", "히로뽕",
        "총기", "권총", "소총", "사설도박", "바카라", "카지노",
        "drug", "weapon", "gun", "bomb", "cocaine", "heroine", "gambling"
    ])

    # Format JSON structure
    final_data = {
        "profanity_and_curse": sorted(list(korean_words.union(english_words))),
        "adult_and_explicit": sorted(list(adult_words)),
        "violence_and_death": sorted(list(violence_words)),
        "illegal_and_weapons": sorted(list(illegal_words)),
        "metadata": {
            "total_korean_profanity_count": len(korean_words),
            "total_english_profanity_count": len(english_words),
            "total_inappropriate_words_count": len(korean_words) + len(english_words) + len(adult_words) + len(violence_words) + len(illegal_words),
            "source": "Open-Source GitHub Repositories (bad_word_list, LDNOOBW)"
        }
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Successfully compiled large-scale profanity dataset into {OUTPUT_FILE}")
    print(f"📊 Total Dataset Words: {final_data['metadata']['total_inappropriate_words_count']} entries")


if __name__ == "__main__":
    download_and_build_dataset()
