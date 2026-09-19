"""Text OCR provider backed by RapidOCR (PaddleOCR onnx models).

Implements core-ocr's OcrTextProvider so it can be injected into
DeviceScenario without touching core-ocr. The bundled CRNN remains a
fallback option.
"""

from typing import TYPE_CHECKING

import cv2
from arcaea_offline_ocr.providers import OcrTextProvider
from cv2.typing import MatLike
from typing_extensions import override

if TYPE_CHECKING:
    pass

# common look-alike confusions when recognizing digit-only ROIs
_DIGIT_CONFUSIONS = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "D": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        "Z": "2",
        "z": "2",
        "S": "5",
        "s": "5",
        "B": "8",
    }
)


class RapidOcrTextProvider(OcrTextProvider):
    # rec-only fallback confidence floor; blank ROIs yield low-confidence junk
    MIN_REC_CONFIDENCE: float = 0.5

    def __init__(self, *, numeric_only: bool = False) -> None:
        from rapidocr import RapidOCR  # noqa: PLC0415

        self._engine: RapidOCR = RapidOCR()
        self._numeric_only: bool = numeric_only

    def _normalize(self, text: str) -> str | None:
        text = text.replace("'", "").replace(" ", "")
        if self._numeric_only:
            text = text.translate(_DIGIT_CONFUSIONS)
            text = "".join(c for c in text if c.isdigit())
        return text or None

    @staticmethod
    def _extract_txts(result: object) -> list[str] | None:
        # rapidocr v2+: RapidOCROutput with .txts; legacy v1: (items, elapses)
        txts = getattr(result, "txts", None)
        if txts is None and isinstance(result, tuple) and result:
            items = result[0]
            txts = [item[1] for item in items] if items else None
        return list(txts) if txts else None

    @override
    def result_raw(self, img: MatLike, /) -> str | None:
        result = self._engine(img)
        txts = self._extract_txts(result)
        if not txts:
            # PaddleOCR detection fails on small single-line crops
            # (e.g. the ~100x24 px PURE/FAR/LOST counters); recognize the
            # whole crop without detection instead
            rec = self._engine(img, use_det=False, use_cls=False, use_rec=True)
            rec_txts = getattr(rec, "txts", None)
            rec_scores = getattr(rec, "scores", None)
            if (
                rec_txts
                and rec_scores is not None
                and max(rec_scores) >= (self.MIN_REC_CONFIDENCE)
            ):
                txts = list(rec_txts)
        if not txts:
            return None
        return self._normalize("".join(txts))

    @override
    def result(self, img: MatLike, /) -> str | None:
        return self.result_raw(img)

    def result_rec_only(self, img: MatLike, /) -> str | None:
        """Recognize a single-line crop without detection.

        For fixed small ROIs (counters, the HIGH SCORE row) detection is
        unreliable - it either finds nothing or produces worse text than
        a direct recognition pass. A replicate border plus 2x upscale
        markedly improves lone-short-digit crops."""
        h, w = img.shape[:2]
        pad = max(2, round(min(h, w) * 0.15))
        padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        resized = cv2.resize(padded, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        rec = self._engine(resized, use_det=False, use_cls=False, use_rec=True)
        txts = getattr(rec, "txts", None)
        scores = getattr(rec, "scores", None)
        if not txts or scores is None or max(scores) < self.MIN_REC_CONFIDENCE:
            return None
        return self._normalize("".join(txts))
