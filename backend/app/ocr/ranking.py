"""Ranking of ImageHashDatabaseIdProvider results into a single best id
plus a distinct candidate list."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arcaea_offline_ocr.providers import ImageIdProviderResult

CANDIDATE_COUNT = 5


def rank_candidates(
    results: Sequence["ImageIdProviderResult"],
) -> tuple[str | None, list[dict[str, str | float]]]:
    """Merge the per-hash-type lookups into one ranking.

    Each hash type is one evidence source: pHash/DCT weighs 4,
    difference 2, average 1. A result without a hash type counts as one
    weight-1 source. A candidate's score is the confidence it earned
    from the sources it matched, divided by the total weight of all
    sources in the result set. A candidate matched by every type
    therefore scores its weighted average, while one matched by fewer
    sources scores proportionally to the weight it earned. Returns the
    top id and the top CANDIDATE_COUNT distinct ids."""
    from arcaea_offline_ocr.providers.ihdb import ImageHashType  # noqa: PLC0415

    weights = {
        ImageHashType.AVERAGE: 1,
        ImageHashType.DIFFERENCE: 2,
        ImageHashType.DCT: 4,
    }
    by_id: dict[str, list[tuple[int, float]]] = {}
    has_typed = has_untyped = False
    for r in results:
        # not every ImageIdProvider carries per-hash-type results; a
        # result without one weighs 1 as a single source
        hash_type = getattr(r, "image_hash_type", None)
        if hash_type is None:
            has_untyped = True
            weight = 1
        else:
            has_typed = True
            weight = weights.get(hash_type, 1)
        by_id.setdefault(r.image_id, []).append((weight, r.confidence))
    total_weight = (sum(weights.values()) if has_typed else 0) + (
        1 if has_untyped else 0
    )
    ranked = sorted(
        (
            (image_id, sum(w * c for w, c in m) / total_weight)
            for image_id, m in by_id.items()
        ),
        key=lambda it: it[1],
        reverse=True,
    )
    if not ranked:
        return None, []
    return ranked[0][0], [
        {"image_id": image_id, "confidence": confidence}
        for image_id, confidence in ranked[:CANDIDATE_COUNT]
    ]
