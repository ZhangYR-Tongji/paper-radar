from datetime import date, timedelta
from math import isfinite

import pytest

from app.models import KeywordGroup, Paper, ScoringWeights, UserPreferences
from app.models.scoring import DEFAULT_SCORING_WEIGHTS
from app.services.keyword_matching import contains_keyword, normalize_text
from app.services.scoring import ScoringContext, calculate_paper_score


def group(name="Robotics", **overrides):
    return KeywordGroup(
        **{
            "name": name,
            "is_enabled": True,
            "priority_weight": 1.0,
            "positive_keywords": ["tendon-driven robot"],
            "required_keywords": [],
            "optional_keywords": [],
            "negative_keywords": [],
            "related_tags": [],
            **overrides,
        }
    )


def paper(**overrides):
    return Paper(
        **{
            "title": "Tendon-driven robot kinematics",
            "abstract": "A robot for endoscopic intervention.",
            "source": "arxiv",
            "published_date": date.today(),
            **overrides,
        }
    )


def score(item=None, groups=None, weights=None, preferences=None, ranked_sources=None):
    return calculate_paper_score(
        item if item is not None else paper(),
        ScoringContext(
            tuple(groups if groups is not None else [group()]),
            ScoringWeights(**(DEFAULT_SCORING_WEIGHTS | (weights or {}))),
            preferences,
            ranked_sources or {},
        ),
    )


def test_adding_unrelated_direction_does_not_dilute_or_penalize_existing_match():
    original = score(groups=[group()])
    additional = group(
        "Aerial manipulation",
        positive_keywords=["aerial manipulation"],
        negative_keywords=["endoscopic intervention"],
        priority_weight=10,
    )
    expanded = score(groups=[group(), additional])
    assert expanded.final_score == original.final_score
    assert expanded.topic_score == original.topic_score
    assert expanded.negative_filter_penalty == 0


def test_alternative_keywords_and_typographic_duplicates_do_not_change_score():
    original = score()
    expanded = score(
        groups=[
            group(
                positive_keywords=[
                    "tendon-driven robot",
                    "TENDON DRIVEN ROBOT",
                    "continuum robot",
                    "cable robot",
                ]
            )
        ]
    )
    assert expanded.final_score == original.final_score
    assert expanded.matched_positive == ["tendon-driven robot"]


def test_title_evidence_is_stronger_than_abstract_evidence():
    title = score(paper(title="Tendon-driven robot", abstract="Kinematics"))
    abstract = score(paper(title="Kinematics", abstract="Tendon-driven robot"))
    assert title.final_score > abstract.final_score >= 60


def test_cold_start_can_reach_highly_relevant_without_feedback_or_method_buzzwords():
    result = score()
    assert result.final_score >= 80
    assert result.classification == "Highly Relevant"
    assert result.method_score == 0


def test_generic_method_words_cannot_recommend_an_unrelated_paper():
    unrelated = score(
        paper(
            title="A clinical survey of network models",
            abstract="A systematic review and evaluation of clinical benchmarks.",
            venue="Journal of Clinical Studies",
        )
    )
    assert unrelated.method_score == 100
    assert unrelated.final_score == 0
    assert score().final_score > unrelated.final_score


def test_optional_terms_and_high_priority_cannot_replace_a_topic_match():
    optional_only = score(
        paper(
            title="Force control and trajectory planning",
            abstract="Simulation, evaluation, physical interaction and visual servoing.",
        ),
        groups=[
            group(
                optional_keywords=[
                    "force control",
                    "trajectory planning",
                    "physical interaction",
                    "visual servoing",
                ],
                priority_weight=100,
            )
        ],
    )
    assert optional_only.final_score <= 35
    assert optional_only.classification == "Filtered"


def test_required_terms_gate_their_own_direction_only():
    restricted = group(required_keywords=["force control"])
    assert score(groups=[restricted]).final_score == 0
    other = group("Endoscopy", positive_keywords=["endoscopic intervention"])
    assert score(groups=[restricted, other]).final_score == score(groups=[other]).final_score


def test_required_only_group_is_valid_but_empty_group_is_not():
    required_only = group(positive_keywords=[], required_keywords=["tendon-driven robot"])
    assert score(groups=[required_only]).final_score >= 80
    assert score(groups=[group(positive_keywords=["", "   "])]).final_score == 0


def test_negative_terms_are_counted_once_and_remain_local_to_each_direction():
    item = paper(abstract="A power-cable inspection experiment in remote sensing.")
    clean = score(item)
    single = score(item, groups=[group(negative_keywords=["power cable", "POWER-CABLE"])])
    double = score(item, groups=[group(negative_keywords=["power cable", "remote sensing"])])
    assert single.negative_filter_penalty == 25
    assert double.negative_filter_penalty == 50
    assert clean.final_score - single.final_score == pytest.approx(5)
    assert single.final_score - double.final_score == pytest.approx(5)
    other = group("Another matching direction")
    best = score(item, groups=[group(negative_keywords=["power cable"]), other])
    assert best.final_score == clean.final_score
    assert best.negative_filter_penalty == 0


def test_base_weight_ratios_are_normalized():
    ratios = {
        key: value * 100
        for key, value in DEFAULT_SCORING_WEIGHTS.items()
        if key in {"topic_weight", "method_weight", "venue_weight", "freshness_weight"}
    }
    assert score(weights=ratios).final_score == score().final_score


def test_neutral_preferences_neither_boost_nor_reduce_score():
    no_preference = score(weights={"user_preference_weight": 0})
    neutral = score(weights={"user_preference_weight": 1}, preferences=UserPreferences())
    assert neutral.final_score == no_preference.final_score


def test_zero_weights_return_a_finite_zero_score():
    result = score(weights=dict.fromkeys(DEFAULT_SCORING_WEIGHTS, 0))
    assert result.final_score == 0
    assert isfinite(result.final_score)


def test_venue_name_is_not_used_as_a_quality_proxy():
    weights = {"venue_weight": 0.2}
    missing = score(paper(venue=None), weights=weights)
    named = score(paper(venue="Journal of Robotics"), weights=weights)
    assert missing.final_score == named.final_score


def test_old_topic_match_outranks_new_supporting_terms():
    old = score(paper(published_date=date.today() - timedelta(days=1000)))
    new = score(
        paper(title="Force control", abstract="Evaluation"),
        groups=[
            group(optional_keywords=["force control"]),
        ],
    )
    assert old.final_score > new.final_score


def test_disabled_sources_and_zero_priority_are_filtered():
    assert score(ranked_sources={"arxiv": False}).final_score == 0
    assert score(groups=[group(is_enabled=False)]).final_score == 0
    assert score(groups=[group(priority_weight=0)]).final_score == 0
    assert score(groups=[]).final_score == 0


@pytest.mark.parametrize(
    ("text", "keyword", "expected"),
    [
        ("TENDON\u2011DRIVEN robots", "tendon driven robot", True),
        ("Endoscopic studies", "study", True),
        ("A robotic farm", "arm", False),
        ("A chair", "AI", False),
        ("模型用于软体机器人控制", "软体机器人", True),
        ("Any paper", "  ", False),
    ],
)
def test_lexical_matching_handles_boundaries_and_typographic_variants(text, keyword, expected):
    assert contains_keyword(normalize_text(text), keyword) is expected


def test_phrases_cannot_cross_title_and_abstract_boundary():
    assert score(paper(title="Tendon-driven", abstract="Robot kinematics")).final_score == 0
