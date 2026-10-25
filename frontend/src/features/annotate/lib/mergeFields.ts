/**
 * Loads an annotation form from a saved row plus an OCR proposal: saved
 * values win, the proposal fills fields the row leaves null, `empty`
 * supplies the rest. Keys in `always` copy from `saved` even when null.
 */
export function mergeFields<F extends object>(
  empty: F,
  prefill: Partial<F> | null | undefined,
  saved: Partial<F> | null | undefined,
  always: readonly (keyof F)[] = [],
): F {
  const merged = { ...empty } as Record<string, unknown>;
  for (const key of Object.keys(empty)) {
    const proposal = prefill?.[key as keyof F];
    if (proposal != null) merged[key] = proposal;
  }
  if (saved != null) {
    for (const key of Object.keys(empty)) {
      const value = saved[key as keyof F];
      if (value != null || always.includes(key as keyof F)) merged[key] = value;
    }
  }
  return merged as F;
}
