import { describe, expect, it } from "vitest";

import { roiCropStyle } from "./roiCropStyle";

describe("roiCropStyle", () => {
  it("scales and offsets the canvas so the rect fills the box", () => {
    // canvas 800x400, rect (100, 50, 200, 100): image renders at 400%
    // box width, shifted left 50% and up 50% of box height
    expect(roiCropStyle([100, 50, 200, 100], [800, 400])).toEqual({
      width: "400%",
      left: "-50%",
      top: "-50%",
    });
  });

  it("maps a full-width rect to an unshifted double-size image", () => {
    // rect spans the whole canvas: image at 100% box width, no shift
    expect(roiCropStyle([0, 0, 800, 400], [800, 400])).toEqual({
      width: "100%",
      left: "0%",
      top: "0%",
    });
  });

  it("keeps the vertical offset in rect space, not canvas space", () => {
    // top% is a fraction of the box height (rect.h), so y=20 of rect
    // height 50 shifts 40% regardless of the canvas height
    expect(roiCropStyle([10, 20, 250, 50], [500, 200])).toEqual({
      width: "200%",
      left: "-4%",
      top: "-40%",
    });
  });
});
