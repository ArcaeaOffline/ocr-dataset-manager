import { describe, expect, it } from "vitest";
import { useBusy } from "./useBusy";

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("useBusy", () => {
  it("runs one action at a time", async () => {
    const { busyAction, withBusy } = useBusy<"a" | "b">();
    const gate = deferred();
    let ranB = false;

    void withBusy("a", () => gate.promise);
    expect(busyAction.value).toBe("a");

    await withBusy("b", async () => {
      ranB = true;
    });
    expect(ranB).toBe(false);
    expect(busyAction.value).toBe("a");

    gate.resolve();
    await gate.promise;
    expect(busyAction.value).toBeNull();
  });
});
