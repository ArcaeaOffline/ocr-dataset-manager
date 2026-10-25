import { describe, expect, it } from "vitest";
import { prefilledKeys, useFieldSources } from "./useFieldSources";

describe("prefilledKeys", () => {
  it("marks fields absent from the saved row and filled by the prefill", () => {
    expect(prefilledKeys(["song_id", "score"], { song_id: "saved" }, { score: 1 })).toEqual([
      "score",
    ]);
    expect(prefilledKeys(["song_id"], null, { song_id: "x" })).toEqual(["song_id"]);
  });

  it("marks nothing when the prefill is absent", () => {
    expect(prefilledKeys(["song_id"], { song_id: "saved" }, null)).toEqual([]);
  });
});

describe("useFieldSources", () => {
  it("clears a field's mark when a different value is written", () => {
    const { form, prefilled, markPrefilled } = useFieldSources({
      song_id: null as string | null,
      score: null as number | null,
    });
    markPrefilled(["song_id", "score"]);
    form.song_id = "user";
    expect([...prefilled]).toEqual(["score"]);
  });

  it("keeps the mark when the same value is re-emitted", () => {
    // pickers re-emit their (prefilled) text when the prop syncs back
    const { form, prefilled, markPrefilled } = useFieldSources({
      song_id: null as string | null,
    });
    markPrefilled(["song_id"]);
    form.song_id = null;
    expect([...prefilled]).toEqual(["song_id"]);
  });

  it("markPrefilled replaces the whole set", () => {
    const { prefilled, markPrefilled } = useFieldSources({
      song_id: null as string | null,
      score: null as number | null,
    });
    markPrefilled(["song_id"]);
    markPrefilled(["score"]);
    expect([...prefilled]).toEqual(["score"]);
  });
});
