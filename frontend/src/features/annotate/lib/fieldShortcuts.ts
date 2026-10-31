import type { ShortcutBinding } from "@/composables/useShortcuts";

/** keys for RATING_CLASS_NAMES order: PST PRS FTR BYD ETR */
export const RATING_KEYS = ["1", "2", "3", "4", "5"] as const;

/** keys for CLEAR_STATUS_NAMES order: TL TC FR PM EC HC */
export const CLEAR_KEYS = ["L", "C", "F", "P", "E", "H"] as const;

export interface FieldShortcutTarget {
  /** current field value; null is the cleared "unknown" state */
  get: () => number | null;
  set: (value: number | null) => void;
}

/**
 * One single-key binding per option, in the key list's order. Pressing
 * the key of the already-selected option clears the field back to null,
 * mirroring the click convention of SegmentedSelect.
 */
export function fieldShortcuts(
  target: FieldShortcutTarget,
  keys: readonly string[],
): ShortcutBinding[] {
  return keys.map((key, value) => ({
    key,
    handler: () => target.set(target.get() === value ? null : value),
  }));
}
