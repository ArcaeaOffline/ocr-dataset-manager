import { describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";
import { useGuardedAction } from "./useGuardedAction";

describe("useGuardedAction", () => {
  it("runs immediately while the gate is closed", () => {
    const { pending, run } = useGuardedAction(() => false, ref("a"));
    let ran = 0;
    run(() => ran++);
    expect(ran).toBe(1);
    expect(pending.value).toBe(false);
  });

  it("defers behind pending until confirmed, then stops asking", () => {
    const { pending, run, confirm } = useGuardedAction(() => true, ref("a"));
    let ran = 0;
    run(() => ran++);
    expect(pending.value).toBe(true);
    expect(ran).toBe(0);

    confirm();
    expect(ran).toBe(1);
    expect(pending.value).toBe(false);

    run(() => ran++);
    expect(ran).toBe(2);
    expect(pending.value).toBe(false);
  });

  it("cancel drops the deferred action without confirming", () => {
    const { pending, run, cancel } = useGuardedAction(() => true, ref("a"));
    let ran = 0;
    run(() => ran++);
    cancel();
    expect(ran).toBe(0);
    expect(pending.value).toBe(false);
  });

  it("re-arms after the scope key changes", async () => {
    const key = ref("a");
    const { pending, run, confirm } = useGuardedAction(() => true, key);
    run(() => {});
    confirm();
    expect(pending.value).toBe(false);

    key.value = "b";
    await nextTick();
    run(() => {});
    expect(pending.value).toBe(true);
  });
});
