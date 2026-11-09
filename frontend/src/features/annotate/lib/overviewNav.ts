export type GridMoveKey = "arrowleft" | "arrowright" | "arrowup" | "arrowdown";

/**
 * Next index after an arrow press on a row-major grid, clamped to the
 * bounds: moves that would leave the grid keep the current index.
 */
export function gridMove(index: number, count: number, columns: number, key: GridMoveKey): number {
  switch (key) {
    case "arrowleft":
      return Math.max(0, index - 1);
    case "arrowright":
      return Math.min(count - 1, index + 1);
    case "arrowup":
      return Math.max(0, index - columns);
    case "arrowdown":
      return Math.min(count - 1, index + columns);
  }
}
