import { shallowReactive } from "vue";

/**
 * Tracks which form fields currently hold the machine prefill proposal.
 * `markPrefilled` replaces the whole set after a programmatic load.
 * writes through the returned form clear a field's mark, so a value the
 * user replaced is no longer reported. A write of the unchanged value
 * keeps the mark: the pickers re-emit their (prefilled) text when the
 * prop syncs back into their input.
 */
export function useFieldSources<T extends object>(form: T) {
  // shallow: the set holds primitive keys only
  const prefilled = shallowReactive(new Set<keyof T>());

  const proxied: T = new Proxy(form, {
    set(target, key, value) {
      if (target[key as keyof T] !== value) {
        prefilled.delete(key as keyof T);
      }
      return Reflect.set(target, key, value);
    },
  });

  function markPrefilled(keys: Iterable<keyof T>) {
    prefilled.clear();
    for (const key of keys) prefilled.add(key);
  }

  return { form: proxied, prefilled, markPrefilled };
}

/** Fields whose loaded value is the prefill proposal: absent from the
 * saved row and non-null in the prefill. */
export function prefilledKeys<K extends string>(
  keys: readonly K[],
  saved: Partial<Record<K, unknown>> | null | undefined,
  prefill: Partial<Record<K, unknown>> | null | undefined,
): K[] {
  return keys.filter((key) => saved?.[key] == null && prefill?.[key] != null);
}
