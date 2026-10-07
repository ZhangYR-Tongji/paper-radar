import re
import unicodedata
from functools import lru_cache


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s_\-\u2010-\u2015]+", " ", text).strip()


def unique_keywords(keywords: list[str]) -> list[str]:
    """Keep one spelling of a term, ignoring empty and typographic duplicates."""
    unique = {}
    for keyword in keywords:
        normalized = normalize_text(keyword)
        if normalized:
            unique.setdefault(normalized, keyword.strip())
    return list(unique.values())


def contains_keyword(normalized_text: str, keyword: str) -> bool:
    normalized = normalize_text(keyword)
    return bool(normalized and _keyword_pattern(normalized).search(normalized_text))


@lru_cache(maxsize=4096)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    pattern = re.escape(keyword)
    # Keep common English plurals without allowing short terms such as "arm"
    # to match inside "farm". This is lexical matching, not semantic expansion.
    last_word = keyword.rsplit(" ", 1)[-1]
    if re.fullmatch(r"[a-z]{3,}", last_word) and not last_word.endswith("s"):
        if last_word.endswith("y") and last_word[-2] not in "aeiou":
            pattern = pattern[:-1] + "(?:y|ies)"
        elif last_word.endswith(("ch", "sh", "x", "z")):
            pattern += "(?:es)?"
        else:
            pattern += "s?"
    if keyword[0].isascii() and keyword[0].isalnum():
        pattern = r"(?<![a-z0-9])" + pattern
    if keyword[-1].isascii() and keyword[-1].isalnum():
        pattern += r"(?![a-z0-9])"
    return re.compile(pattern)
