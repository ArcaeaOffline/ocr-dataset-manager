import { onMounted, onUnmounted } from "vue";

export interface ShortcutBinding {
  /** event.key, matched case-insensitively */
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  /** fire while focus sits in a text field. Write chords (Ctrl+S) set
      this; letters and digits must not steal typing */
  allowInTextField?: boolean;
  /** extra per-binding gate on top of the composable-wide one */
  enabled?: () => boolean;
  handler: (event: KeyboardEvent) => void;
}

/** the matcher's event subset; plain objects keep it testable without a DOM */
export interface ShortcutEvent {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
}

/**
 * The first binding whose key and modifier state match the event. A
 * ctrl binding matches Ctrl or Cmd, so macOS Cmd+S saves instead of
 * falling through to the plain-S binding. Alt compares exactly, and
 * modifiers in general keep Ctrl+S and S distinct bindings. Shift is
 * not matched: "?" is Shift+/ on most layouts, and no binding gives a
 * shifted key its own action.
 */
export function matchShortcut(
  event: ShortcutEvent,
  bindings: ShortcutBinding[],
): ShortcutBinding | null {
  const key = event.key.toLowerCase();
  return (
    bindings.find(
      (binding) =>
        binding.key.toLowerCase() === key &&
        (event.ctrlKey || event.metaKey) === (binding.ctrl ?? false) &&
        (binding.alt ?? false) === event.altKey,
    ) ?? null
  );
}

function inTextField(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
  );
}

/** segmented selects keep roving focus inside a role=group subtree */
function inRovingFocusGroup(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.closest('[role="group"]') != null;
}

/**
 * Registers window-level keyboard shortcuts for the calling component.
 * The binding getter runs per event, so it may close over changing
 * refs. Everything goes inert while `enabled` is false (open dialogs,
 * an inactive flow, ...); IME composition always wins. Matched events
 * are preventDefault-ed, which is what keeps Ctrl+S away from the
 * browser's save dialog.
 */
export function useShortcuts(
  getBindings: () => ShortcutBinding[],
  options: { enabled?: () => boolean } = {},
): void {
  function onKeydown(event: KeyboardEvent) {
    // one action per physical press: auto-repeat would flip toggle
    // bindings between value and null at typing speed
    if (event.repeat) return;
    if (event.isComposing) return;
    if (options.enabled && !options.enabled()) return;
    const binding = matchShortcut(event, getBindings());
    if (binding == null) return;
    if (binding.enabled && !binding.enabled()) return;
    if (
      !binding.allowInTextField &&
      (inTextField(event.target) || inRovingFocusGroup(event.target))
    ) {
      return;
    }
    event.preventDefault();
    binding.handler(event);
  }

  onMounted(() => window.addEventListener("keydown", onKeydown));
  onUnmounted(() => window.removeEventListener("keydown", onKeydown));
}
