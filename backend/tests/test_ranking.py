import pytest
from arcaea_offline_ocr.providers import ImageCategory
from arcaea_offline_ocr.providers.base import ImageIdProviderResult
from arcaea_offline_ocr.providers.ihdb import (
    ImageHashDatabaseIdProviderResult,
    ImageHashType,
)

from app.ocr.ranking import rank_candidates


def _typed(
    image_id: str,
    hash_type: ImageHashType,
    confidence: float,
) -> ImageHashDatabaseIdProviderResult:
    return ImageHashDatabaseIdProviderResult(
        image_id=image_id,
        category=ImageCategory.PARTNER_ICON,
        confidence=confidence,
        image_hash_type=hash_type,
    )


def test_consistent_match_outranks_isolated_high_confidence() -> None:
    # without the total-weight denominator, an id present in only one
    # type's list keeps its raw confidence and outranks the id matched
    # by all three
    results = [
        _typed("truth", ImageHashType.AVERAGE, 0.953),
        _typed("truth", ImageHashType.DIFFERENCE, 0.863),
        _typed("truth", ImageHashType.DCT, 0.805),
        _typed("noise", ImageHashType.AVERAGE, 0.895),
    ]
    top, candidates = rank_candidates(results)
    assert top == "truth"
    assert candidates[0] == {
        "image_id": "truth",
        "confidence": pytest.approx((1 * 0.953 + 2 * 0.863 + 4 * 0.805) / 7, abs=1e-9),
    }
    assert candidates[1] == {
        "image_id": "noise",
        "confidence": pytest.approx(0.895 / 7, abs=1e-4),
    }


def test_full_match_score_equals_weighted_average() -> None:
    # matched weight equals total weight, so the score is the plain
    # weighted average
    results = [
        _typed("a", ImageHashType.AVERAGE, 0.9),
        _typed("a", ImageHashType.DIFFERENCE, 0.8),
        _typed("a", ImageHashType.DCT, 0.7),
    ]
    top, candidates = rank_candidates(results)
    assert top == "a"
    expected = (1 * 0.9 + 2 * 0.8 + 4 * 0.7) / 7
    assert candidates[0]["confidence"] == pytest.approx(expected, abs=1e-9)


def test_dct_evidence_outweighs_average() -> None:
    results = [
        _typed("dct-only", ImageHashType.DCT, 0.8),
        _typed("avg-only", ImageHashType.AVERAGE, 0.9),
    ]
    top, _ = rank_candidates(results)
    assert top == "dct-only"


def test_partial_match_scores_below_full_match_of_equal_quality() -> None:
    # same per-type confidence, one source fewer -> strictly lower score
    both = [
        _typed("both", ImageHashType.AVERAGE, 0.8),
        _typed("both", ImageHashType.DCT, 0.8),
    ]
    one = [_typed("one", ImageHashType.AVERAGE, 0.8)]
    _, c_both = rank_candidates(both)
    _, c_one = rank_candidates(one)
    assert float(c_both[0]["confidence"]) > float(c_one[0]["confidence"])


def test_untyped_results_keep_plain_confidence() -> None:
    # a provider without hash types is the only source, so the score
    # stays on the confidence scale
    results = [
        ImageIdProviderResult(
            image_id="x", category=ImageCategory.JACKET, confidence=0.9
        ),
        ImageIdProviderResult(
            image_id="y", category=ImageCategory.JACKET, confidence=0.7
        ),
    ]
    top, candidates = rank_candidates(results)
    assert top == "x"
    assert candidates[0]["confidence"] == pytest.approx(0.9)


def test_empty_results() -> None:
    assert rank_candidates([]) == (None, [])


def test_candidate_list_is_distinct_and_capped() -> None:
    results = [
        _typed(f"id{i}", ImageHashType.AVERAGE, 0.5 - i * 0.05) for i in range(8)
    ]
    _, candidates = rank_candidates(results)
    assert len(candidates) == 5
    assert len({c["image_id"] for c in candidates}) == 5
