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

    An id matched by several hash types gets one entry whose confidence
    is the weighted average over the types it actually matched with
    (pHash/DCT weighs 4, difference 2, average 1). Returns
    the top id and the top CANDIDATE_COUNT distinct ids."""
    from arcaea_offline_ocr.providers.ihdb import ImageHashType  # noqa: PLC0415

    weights = {
        ImageHashType.AVERAGE: 1,
        ImageHashType.DIFFERENCE: 2,
        ImageHashType.DCT: 4,
    }
    by_id: dict[str, list[tuple[int, float]]] = {}
    for r in results:
        # chieri results arrive as the base ImageIdProviderResult, which
        # carries no hash type; those weigh 1 like single-type matches
        hash_type = getattr(r, "image_hash_type", None)
        weight = 1 if hash_type is None else weights.get(hash_type, 1)
        by_id.setdefault(r.image_id, []).append((weight, r.confidence))
    ranked = sorted(
        (
            (image_id, sum(w * c for w, c in m) / sum(w for w, _ in m))
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
