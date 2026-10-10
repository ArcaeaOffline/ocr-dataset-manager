"""B30/B50 layout recognizers, keyed by `b30_results.layout` id."""

from .arcaeaonline import ArcaeaonlineB30Ocr, ArcaeaonlineB50Ocr
from .base import (
    ARCAEAONLINE_B30,
    ARCAEAONLINE_B50,
    CHIERI_V4,
    YURISAKI_B50,
    B30Layout,
    B30LayoutOcr,
    ComponentOcr,
)
from .chieri_v4 import ChieriV4Ocr
from .providers import OcrProviders
from .yurisaki import YurisakiOcr

RECOGNIZERS: dict[str, type[B30LayoutOcr]] = {
    YURISAKI_B50.id: YurisakiOcr,
    ARCAEAONLINE_B30.id: ArcaeaonlineB30Ocr,
    ARCAEAONLINE_B50.id: ArcaeaonlineB50Ocr,
    CHIERI_V4.id: ChieriV4Ocr,
}

LAYOUTS: dict[str, B30Layout] = {
    YURISAKI_B50.id: YURISAKI_B50,
    ARCAEAONLINE_B30.id: ARCAEAONLINE_B30,
    ARCAEAONLINE_B50.id: ARCAEAONLINE_B50,
    CHIERI_V4.id: CHIERI_V4,
}


def make_recognizer(layout_id: str) -> B30LayoutOcr:
    return RECOGNIZERS[layout_id]()


__all__ = [
    "LAYOUTS",
    "RECOGNIZERS",
    "B30Layout",
    "B30LayoutOcr",
    "ComponentOcr",
    "OcrProviders",
    "make_recognizer",
]
