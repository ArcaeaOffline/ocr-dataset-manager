import { ref, watch, type Ref } from "vue";

/**
 * Runs actions behind a one-time confirmation. `run(action)` executes
 * immediately while `gate()` is false or after the user confirmed.
 * otherwise the action is deferred and `pending` turns true for the
 * caller's confirm dialog (`confirm` runs it, `cancel` drops it). The
 * confirmation resets whenever `scopeKey` changes.
 */
export function useGuardedAction(gate: () => boolean, scopeKey: Ref<unknown>) {
  const pending = ref(false);
  const confirmed = ref(false);
  let deferred: (() => void) | null = null;

  watch(scopeKey, () => {
    confirmed.value = false;
    deferred = null;
    pending.value = false;
  });

  function run(action: () => void): void {
    if (!gate() || confirmed.value) {
      action();
      return;
    }
    deferred = action;
    pending.value = true;
  }

  function confirm(): void {
    confirmed.value = true;
    pending.value = false;
    const action = deferred;
    deferred = null;
    action?.();
  }

  function cancel(): void {
    deferred = null;
    pending.value = false;
  }

  return { pending, run, confirm, cancel };
}
