import { ref } from "vue";

/** serializes button actions: one in-flight action at a time; busyAction
 * lets buttons disable themselves and swap in a spinner */
export function useBusy<T extends string>() {
  const busyAction = ref<T | null>(null);

  async function withBusy(action: T, run: () => Promise<void>) {
    if (busyAction.value !== null) return;
    busyAction.value = action;
    try {
      await run();
    } finally {
      busyAction.value = null;
    }
  }

  return { busyAction, withBusy };
}
