import { describe, expect, it } from "vitest";
import { formatEarlyLate, formatScore, formatScoreDelta } from "./displayFormat";

describe("formatScore", () => {
  it("zero-pads to 8 digits and groups with apostrophes", () => {
    expect(formatScore(9123456)).toBe("09'123'456");
    expect(formatScore(10000000)).toBe("10'000'000");
    expect(formatScore(0)).toBe("00'000'000");
  });

  it("renders no text for null, negative and non-integer values", () => {
    expect(formatScore(null)).toBeNull();
    expect(formatScore(-1)).toBeNull();
    expect(formatScore(1.5)).toBeNull();
  });
});

describe("formatScoreDelta", () => {
  it("signs a padded 8-digit score", () => {
    expect(formatScoreDelta(1234)).toBe("+00'001'234");
    expect(formatScoreDelta(-1234)).toBe("-00'001'234");
    expect(formatScoreDelta(0)).toBe("+00'000'000");
  });

  it("renders no text for null and non-integer values", () => {
    expect(formatScoreDelta(null)).toBeNull();
    expect(formatScoreDelta(1.5)).toBeNull();
  });
});

describe("formatEarlyLate", () => {
  it("rebuilds the line with PURE parts when filled", () => {
    expect(formatEarlyLate({ far_late: 12, pure_late: 34, far_early: 56, pure_early: 78 })).toBe(
      "L12(P34) E56(P78)",
    );
  });

  it("drops each PURE part left unfilled", () => {
    expect(
      formatEarlyLate({ far_late: 12, pure_late: null, far_early: 56, pure_early: null }),
    ).toBe("L12 E56");
    expect(formatEarlyLate({ far_late: 12, pure_late: 34, far_early: 56, pure_early: null })).toBe(
      "L12(P34) E56",
    );
  });

  it("renders no line without the far values", () => {
    expect(
      formatEarlyLate({ far_late: null, pure_late: 1, far_early: 2, pure_early: 3 }),
    ).toBeNull();
    expect(
      formatEarlyLate({ far_late: 1, pure_late: null, far_early: null, pure_early: null }),
    ).toBeNull();
  });
});
