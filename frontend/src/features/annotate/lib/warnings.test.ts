import { describe, expect, it } from "vitest";
import type { ResultFields } from "@/api";
import { computeWarnings, voteHint } from "./warnings";

const base: ResultFields = {
  rois_type: null,
  song_id: null,
  partner_id: null,
  rating_class: null,
  clear_status: null,
  score: null,
  pure: null,
  far: null,
  lost: null,
  max_recall: null,
  high_score: null,
  high_score_delta: null,
  pure_shiny: null,
  pure_early: null,
  pure_late: null,
  far_early: null,
  far_late: null,
  checked: false,
};

function fields(overrides: Partial<ResultFields>): ResultFields {
  return { ...base, ...overrides };
}

describe("computeWarnings", () => {
  it("stays silent when nothing is filled in", () => {
    expect(computeWarnings(fields({}))).toEqual([]);
  });

  it("accepts a self-consistent record", () => {
    const warnings = computeWarnings(
      fields({
        score: 9_000_000,
        pure: 100,
        pure_shiny: 80,
        pure_early: 10,
        pure_late: 10,
        far: 5,
        far_early: 2,
        far_late: 3,
        lost: 1,
        max_recall: 105,
        high_score: 8_000_000,
        high_score_delta: 1_000_000,
      }),
    );
    expect(warnings).toEqual([]);
  });

  it("flags pure not splitting into shiny + early + late", () => {
    const warnings = computeWarnings(
      fields({ pure: 100, pure_shiny: 80, pure_early: 10, pure_late: 5 }),
    );
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toContain("pure");
  });

  it("flags far not splitting into early + late", () => {
    expect(computeWarnings(fields({ far: 5, far_early: 2, far_late: 2 }))).toHaveLength(1);
  });

  it("requires max_recall = pure + far when lost is 0", () => {
    const warnings = computeWarnings(fields({ lost: 0, pure: 10, far: 5, max_recall: 20 }));
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toContain("max_recall");
  });

  it("caps max_recall at pure + far when lost is positive", () => {
    expect(computeWarnings(fields({ lost: 3, pure: 10, far: 5, max_recall: 16 }))).toHaveLength(1);
  });

  it("flags impossible scores", () => {
    expect(computeWarnings(fields({ score: 0 }))).toHaveLength(1);
    expect(computeWarnings(fields({ score: 10_010_001 }))).toHaveLength(1);
  });

  it("flags clear types contradicting the counters", () => {
    expect(computeWarnings(fields({ clear_status: 2, lost: 1 }))).toHaveLength(1);
    expect(computeWarnings(fields({ clear_status: 3, far: 1 }))).toHaveLength(1);
  });

  it("flags high_score + delta missing the score", () => {
    expect(
      computeWarnings(fields({ score: 100, high_score: 90, high_score_delta: 5 })),
    ).toHaveLength(1);
  });
});

describe("voteHint", () => {
  it("stays quiet without votes or with a single bucket", () => {
    expect(voteHint(null)).toBeNull();
    expect(voteHint(undefined)).toBeNull();
    expect(voteHint([3])).toBeNull();
  });

  it("surfaces a near tie between the top two buckets", () => {
    expect(voteHint([5, 4, 0, 0, 0])).toContain("5 / 4 / 0 / 0 / 0");
  });

  it("stays quiet on a clear winner", () => {
    expect(voteHint([0, 9, 0, 0, 0])).toBeNull();
  });
});
