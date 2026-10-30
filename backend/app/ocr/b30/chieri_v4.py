"""Adapter presenting core-ocr's ChieriBotV4 scenario through the local
B30 recognizer interface. The scenario's per-hash-type song id results
are re-ranked with the shared weighted ranking for consistency with the
other layouts. Its P/F/L numbers carry no shiny count."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from .base import CHIERI_V4, B30LayoutOcr, ComponentOcr

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from .providers import OcrProviders


class ChieriV4Ocr(B30LayoutOcr):
    layout = CHIERI_V4

    def __init__(self) -> None:
        self._scenario = None
        self._providers: OcrProviders | None = None

    def _ensure_scenario(self, providers: OcrProviders):
        # cheap to build (no model loading), but only usable with a live
        # provider bundle, so it is created on first use and reused while
        # the bundle stays the same
        if self._scenario is None or self._providers is not providers:
            from arcaea_offline_ocr.scenarios.b30 import ChieriBotV4Best30Scenario

            self._scenario = ChieriBotV4Best30Scenario(
                score_provider=providers.text,
                pfl_provider=providers.text,
                image_id_provider=providers.ihdb,
            )
            self._providers = providers
        return self._scenario

    @override
    def component_count(self) -> int:
        return self.layout.component_count

    @override
    def components(self, img: MatLike, providers: OcrProviders) -> list[MatLike]:
        scenario = self._ensure_scenario(providers)
        return scenario.components(img)

    @override
    def ocr_component(
        self, component_bgr: MatLike, index: int, providers: OcrProviders
    ) -> ComponentOcr:
        from ..ranking import rank_candidates

        scenario = self._ensure_scenario(providers)
        ocr = scenario.result(component_bgr)
        song_id, candidates = rank_candidates(ocr.song_id_results)
        return ComponentOcr(
            index=index,
            song_id=song_id,
            song_id_candidates=candidates,
            rating_class=ocr.rating_class or None,
            score=ocr.score or None,
            pure=ocr.pure,
            far=ocr.far,
            lost=ocr.lost,
        )
