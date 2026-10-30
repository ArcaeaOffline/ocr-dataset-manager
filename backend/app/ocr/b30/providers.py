"""Provider bundle handed to B30 layout recognizers.

The providers are owned by the prefill service (singletons behind its
compute lock). Recognizers only receive them."""

from __future__ import annotations

from dataclasses import dataclass

from arcaea_offline_ocr.providers import ImageHashDatabaseIdProvider
from cv2.typing import MatLike

from ..rapid_ocr_provider import RapidOcrTextProvider


@dataclass(frozen=True)
class OcrProviders:
    # numeric-normalized recognition, for plain digit fields
    text: RapidOcrTextProvider
    # structure-preserving recognition, for mixed text fields
    raw: RapidOcrTextProvider
    ihdb: ImageHashDatabaseIdProvider

    def rec_only_int(self, roi: MatLike) -> int | None:
        from ..parsing import parse_int  # noqa: PLC0415

        return parse_int(self.text.result_rec_only(roi))
