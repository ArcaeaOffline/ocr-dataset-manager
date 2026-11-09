import { describe, expect, it } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import { openDialogCount, useDialogOpenTracker } from "./dialogOpen";

describe("useDialogOpenTracker", () => {
  it("counts a dialog from closed to open and back", async () => {
    const open = ref(false);
    const scope = effectScope();
    scope.run(() => useDialogOpenTracker(() => open.value));
    expect(openDialogCount.value).toBe(0);

    open.value = true;
    await nextTick();
    expect(openDialogCount.value).toBe(1);

    open.value = false;
    await nextTick();
    expect(openDialogCount.value).toBe(0);
    scope.stop();
  });

  it("counts a dialog that mounts already open", async () => {
    const open = ref(true);
    const scope = effectScope();
    scope.run(() => useDialogOpenTracker(() => open.value));
    await nextTick();
    expect(openDialogCount.value).toBe(1);
    scope.stop();
  });

  it("releases the slot when the scope stops while open", async () => {
    const open = ref(false);
    const scope = effectScope();
    scope.run(() => useDialogOpenTracker(() => open.value));
    open.value = true;
    await nextTick();
    expect(openDialogCount.value).toBe(1);

    scope.stop();
    expect(openDialogCount.value).toBe(0);
  });
});
