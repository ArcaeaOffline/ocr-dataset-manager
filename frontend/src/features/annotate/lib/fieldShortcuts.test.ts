import { describe, expect, it } from "vitest";
import { fieldShortcuts } from "./fieldShortcuts";

// the handlers ignore the event; node has no KeyboardEvent to build
const event = {} as KeyboardEvent;

describe("fieldShortcuts", () => {
  it("writes the option value at the pressed key's position", () => {
    let stored: number | null = null;
    const bindings = fieldShortcuts({ get: () => stored, set: (value) => (stored = value) }, [
      "1",
      "2",
      "3",
    ]);
    expect(bindings.map((b) => b.key)).toEqual(["1", "2", "3"]);

    bindings[1]?.handler(event);
    expect(stored).toBe(1);
  });

  it("clears back to null when the pressed key already matches", () => {
    let stored: number | null = 1;
    const bindings = fieldShortcuts({ get: () => stored, set: (value) => (stored = value) }, [
      "1",
      "2",
    ]);

    bindings[1]?.handler(event);
    expect(stored).toBeNull();

    bindings[1]?.handler(event);
    expect(stored).toBe(1);
  });
});
