import {
  onWatcherCleanup,
  ref,
  shallowRef,
  toValue,
  watch,
  type MaybeRefOrGetter,
  type Ref,
} from "vue";

/**
 * JSON-serializable source values. The request re-runs when this value
 * changes structurally, so it must fully encode everything `fetcher` reads.
 */
export type RequestKey =
  | string
  | number
  | boolean
  | null
  | readonly RequestKey[]
  | { readonly [key: string]: RequestKey };

export interface UseRequestOptions<T> {
  /** Value of `data` before the first successful load. */
  initialData: T;
  /** Fetch on setup. Defaults to true. */
  immediate?: boolean;
  onError?: (error: Error) => void;
}

/**
 * Runs `fetcher` whenever `source` changes, keeping data/loading/error and
 * discarding stale responses from superseded or disposed runs. Data of a
 * failed run is left untouched. The source is compared structurally
 * (JSON-serialized), so a fresh but equal array/object key does not
 * re-trigger.
 */
export function useRequest<S extends RequestKey, T>(
  source: MaybeRefOrGetter<S>,
  fetcher: (value: S) => Promise<T>,
  options: UseRequestOptions<T>,
) {
  // shallow: fetch results are replaced wholesale on each run, and deep
  // reactivity over item lists is pure overhead
  const data = shallowRef(options.initialData) as Ref<T>;
  const error = ref<Error | null>(null);
  const loading = ref(false);
  let seq = 0;

  async function run(value: S) {
    const id = ++seq;
    loading.value = true;
    error.value = null;
    try {
      const result = await fetcher(value);
      if (id === seq) data.value = result;
    } catch (e) {
      if (id !== seq) return;
      error.value = e instanceof Error ? e : new Error(String(e));
      options.onError?.(error.value);
    } finally {
      if (id === seq) loading.value = false;
    }
  }

  watch(
    () => JSON.stringify(toValue(source)),
    () => {
      onWatcherCleanup(() => {
        seq++;
      });
      void run(toValue(source));
    },
    { immediate: options.immediate ?? true },
  );

  return { data, error, loading, refresh: () => run(toValue(source)) };
}
