import { describe, expect, it } from "vitest";

import { readQueueTraversal } from "./queueContext";

describe("readQueueTraversal", () => {
  it("passes the queue view's context through", () => {
    expect(
      readQueueTraversal({
        category: "checked",
        order_by: "original_filename",
        direction: "asc",
      }),
    ).toEqual({ category: "checked", order_by: "original_filename", direction: "asc" });
  });

  it("drops values outside the walk's allowed set", () => {
    // the hidden category is a queue view state with no traversal
    expect(readQueueTraversal({ category: "hidden" })).toEqual({});
    expect(readQueueTraversal({ order_by: "bogus", direction: "sideways" })).toEqual({});
  });

  it("treats missing and repeated params as absent", () => {
    expect(readQueueTraversal({})).toEqual({});
    expect(readQueueTraversal({ category: ["all", "checked"] })).toEqual({});
    expect(readQueueTraversal({ category: null })).toEqual({});
  });
});
