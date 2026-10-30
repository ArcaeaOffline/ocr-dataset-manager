/** [x, y, w, h] on the black-edge-cropped image, as served by
 * `/device_rois`. */
export type RoiRect = [number, number, number, number];

/** A field's crop window: the cropped-image URL plus where the window
 * sits on it. */
export interface FieldCrop {
  src: string;
  rect: RoiRect;
  canvas: [number, number];
}

/**
 * CSS offsets that turn a box of aspect `rect.w / rect.h` into a window
 * onto `rect` of the full canvas: the inner image is scaled to
 * `canvas.w / rect.w` box widths and shifted by percentage offsets. Left
 * and width resolve against the box width, top against its height (the
 * box height is fixed by aspect-ratio), so no pixel measurements are
 * needed.
 */
export function roiCropStyle(rect: RoiRect, canvas: [number, number]): Record<string, string> {
  const [x, y, w] = rect;
  return {
    width: `${(100 * canvas[0]) / w}%`,
    left: `${(-100 * x) / w}%`,
    top: `${(-100 * y) / rect[3]}%`,
  };
}
