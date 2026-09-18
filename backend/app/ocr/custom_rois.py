"""Custom ROIs for result-screen fields core-ocr does not cover: the
HIGH SCORE row, the PURE shiny count, and the early/late line.

Rects are derived from det-box measurements on 1080p samples of both
layouts and expressed with the same anchors core-ocr uses (w_mid and
layout_area_h_mid, scaled by the layout factor), so they follow the
rendered UI across resolutions. T1 does not display pure early/late;
its early/late line only carries far values."""

from arcaea_offline_ocr.scenarios.device.rois.auto import (
    DeviceRoisAutoT1,
    DeviceRoisAutoT2,
)
from arcaea_offline_ocr.types import XYWHRect


class CustomRoisT1(DeviceRoisAutoT1):
    @property
    def high_score(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid - 64 * self.factor,
            self.layout_area_h_mid - 57 * self.factor,
            186 * self.factor,
            40 * self.factor,
        )

    @property
    def high_score_delta(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid + 130 * self.factor,
            self.layout_area_h_mid - 57 * self.factor,
            118 * self.factor,
            40 * self.factor,
        )

    @property
    def pure_shiny(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid + 76 * self.factor,
            self.layout_area_h_mid + 111 * self.factor,
            62 * self.factor,
            30 * self.factor,
        )

    @property
    def early_late(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid + 74 * self.factor,
            self.layout_area_h_mid + 146 * self.factor,
            70 * self.factor,
            32 * self.factor,
        )


class CustomRoisT2(DeviceRoisAutoT2):
    @property
    def high_score(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid - 20 * self.factor,
            self.layout_area_h_mid - 85 * self.factor,
            190 * self.factor,
            55 * self.factor,
        )

    @property
    def high_score_delta(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid + 190 * self.factor,
            self.layout_area_h_mid - 85 * self.factor,
            160 * self.factor,
            55 * self.factor,
        )

    @property
    def pure_shiny(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid + 113 * self.factor,
            self.layout_area_h_mid + 158 * self.factor,
            108 * self.factor,
            56 * self.factor,
        )

    @property
    def early_late(self) -> XYWHRect:
        return XYWHRect(
            self.w_mid + 112 * self.factor,
            self.layout_area_h_mid + 213 * self.factor,
            275 * self.factor,
            62 * self.factor,
        )
