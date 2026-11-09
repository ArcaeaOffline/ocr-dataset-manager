import { describe, expect, it } from "vitest";
import { gridMove } from "./overviewNav";

describe("gridMove", () => {
  // a 3x4 grid, 12 entries, row-major
  const count = 12;
  const columns = 4;

  it("moves within a row", () => {
    expect(gridMove(5, count, columns, "arrowleft")).toBe(4);
    expect(gridMove(5, count, columns, "arrowright")).toBe(6);
  });

  it("moves across rows", () => {
    expect(gridMove(5, count, columns, "arrowup")).toBe(1);
    expect(gridMove(5, count, columns, "arrowdown")).toBe(9);
  });

  it("keeps the index at the edges", () => {
    expect(gridMove(0, count, columns, "arrowleft")).toBe(0);
    expect(gridMove(0, count, columns, "arrowup")).toBe(0);
    expect(gridMove(11, count, columns, "arrowright")).toBe(11);
    expect(gridMove(11, count, columns, "arrowdown")).toBe(11);
  });
});
