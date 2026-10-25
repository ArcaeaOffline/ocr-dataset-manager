import { describe, expect, it } from "vitest";
import { mergeFields } from "./mergeFields";

interface Fields {
  song_id: string | null;
  score: number | null;
}

const empty: Fields = { song_id: null, score: null };

describe("mergeFields", () => {
  it("keeps the empty defaults when nothing is saved", () => {
    expect(mergeFields(empty, null, null)).toEqual(empty);
  });

  it("fills unset fields from the prefill only", () => {
    expect(mergeFields(empty, { song_id: "a", score: null }, null)).toEqual({
      song_id: "a",
      score: null,
    });
  });

  it("lets saved values win over the prefill", () => {
    expect(mergeFields(empty, { song_id: "a", score: 1 }, { song_id: "b", score: null })).toEqual({
      song_id: "b",
      score: 1,
    });
  });

  it("copies always-keys from the saved row even when null there", () => {
    // song_id is null in the saved row; without the always-key the
    // prefill proposal would win
    expect(mergeFields(empty, { song_id: "a" }, { song_id: null }, ["song_id"])).toEqual({
      song_id: null,
      score: null,
    });
  });
});
