import hashlib
import math
from dataclasses import dataclass, field

from app.models.keyword_group import KeywordGroup
from app.models.paper import Paper
from app.services.keyword_matching import unique_keywords

TEXT_VERSION = "paper-radar-semantic-v1"


def text_hash(value: str) -> str:
    return hashlib.sha256(f"{TEXT_VERSION}\n{value}".encode()).hexdigest()


def paper_text(paper: Paper) -> str:
    # The encoder truncates at its token limit. Put the title first, then the
    # abstract; do not add source/venue words that can obscure the topic.
    return f"{(paper.title or '').strip()}\n{(paper.abstract or '').strip()}".strip()[:6000]


def group_text(group: KeywordGroup) -> str:
    keywords = unique_keywords(
        [
            *(group.positive_keywords or []),
            *(group.required_keywords or []),
        ]
    )
    description = (group.description or "").strip()
    if not description and not keywords:
        return ""
    return "\n".join(
        filter(
            None,
            [
                (group.name or "").strip(),
                description,
                "; ".join(keywords[:20]),
            ],
        )
    )[:3000]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("Embedding dimensions do not match.")
    if not all(math.isfinite(value) for value in [*left, *right]):
        raise ValueError("Embedding contains non-finite values.")
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if denominator == 0:
        raise ValueError("Embedding has zero norm.")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True)) / denominator))


def similarity_to_score(similarity: float, threshold: float) -> float:
    if not math.isfinite(similarity) or similarity < threshold:
        return 0.0
    # E5 similarities have a high baseline; do not interpret cosine * 100 as
    # relevance or a probability. Above the explicit gate, map evidence to a
    # bounded topic scale. These are adjustable heuristics, not a fitted model.
    upper = min(1.0, max(0.92, threshold + 0.02))
    return min(100.0, 60.0 + 40.0 * (similarity - threshold) / (upper - threshold))


@dataclass(frozen=True)
class SemanticMatch:
    similarity: float
    score: float


@dataclass(frozen=True)
class SemanticEvidence:
    enabled: bool = False
    min_similarity: float = 0.80
    weight: float = 0.90
    model: str = ""
    status: str = "disabled"
    error: str | None = None
    index_key: str = ""
    complete: set[str] = field(default_factory=set)
    matches: dict[str, dict[str, SemanticMatch]] = field(default_factory=dict)
