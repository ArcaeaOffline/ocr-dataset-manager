import { ref, watch, onScopeDispose } from "vue";

/** dialogs currently open anywhere in the app */
export const openDialogCount = ref(0);

/**
 * Counts one dialog's open state in `openDialogCount`. Call from a dialog
 * wrapper's setup; the scope dispose covers an unmount with the dialog
 * still open (e.g. a route change).
 */
export function useDialogOpenTracker(open: () => boolean): void {
  let wasOpen = false;
  watch(
    open,
    (value) => {
      if (value === wasOpen) return;
      wasOpen = value;
      openDialogCount.value += value ? 1 : -1;
    },
    { immediate: true },
  );
  onScopeDispose(() => {
    if (wasOpen) openDialogCount.value -= 1;
  });
}
