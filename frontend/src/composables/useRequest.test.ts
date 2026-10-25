import { describe, expect, it } from "vitest";
import { ref } from "vue";
import { useRequest } from "./useRequest";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

// a macrotask boundary flushes every microtask the request chain queued
const flush = () => new Promise((resolve) => setTimeout(resolve));

describe("useRequest", () => {
  it("serves initialData until the first fetch lands", async () => {
    const d = deferred<string>();
    const { data, loading } = useRequest("key", () => d.promise, { initialData: "init" });

    expect(data.value).toBe("init");
    expect(loading.value).toBe(true);

    d.resolve("loaded");
    await flush();
    expect(data.value).toBe("loaded");
    expect(loading.value).toBe(false);
  });

  it("discards the response of a superseded run", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const source = ref<"a" | "b">("a");
    const fetcher = (key: "a" | "b") => (key === "a" ? first.promise : second.promise);
    const { data, error } = useRequest(source, fetcher, { initialData: "init" });

    source.value = "b";
    first.resolve("stale");
    await flush();
    expect(data.value).toBe("init");

    second.resolve("fresh");
    await flush();
    expect(data.value).toBe("fresh");
    expect(error.value).toBeNull();
  });

  it("ignores the failure of a superseded run", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const source = ref<"a" | "b">("a");
    const errors: Error[] = [];
    const fetcher = (key: "a" | "b") => (key === "a" ? first.promise : second.promise);
    const { data, loading } = useRequest(source, fetcher, {
      initialData: "init",
      onError: (e) => errors.push(e),
    });

    source.value = "b";
    first.resolve("stale but fine");
    await flush();
    expect(data.value).toBe("init");
    expect(errors).toEqual([]);

    second.resolve("fresh");
    await flush();
    expect(data.value).toBe("fresh");
    expect(loading.value).toBe(false);
  });

  it("reports errors and leaves data untouched", async () => {
    const d = deferred<string>();
    d.reject(new Error("boom"));
    const errors: Error[] = [];
    const { data, loading, error } = useRequest("key", () => d.promise, {
      initialData: "init",
      onError: (e) => errors.push(e),
    });

    await flush();
    expect(data.value).toBe("init");
    expect(loading.value).toBe(false);
    expect(error.value?.message).toBe("boom");
    expect(errors).toHaveLength(1);
  });

  it("does not refetch on a structurally equal source change", async () => {
    const source = ref(1);
    const spy = { calls: 0 };
    const { data } = useRequest(
      () => [source.value] as const,
      async () => {
        spy.calls++;
        return `run-${spy.calls}`;
      },
      { initialData: "" },
    );
    await flush();
    source.value = 1;
    await flush();
    expect(spy.calls).toBe(1);
    expect(data.value).toBe("run-1");
  });

  it("refresh reruns the fetcher with the current source", async () => {
    const source = ref("a");
    let n = 0;
    const { data, refresh } = useRequest(source, async () => `run-${++n}`, { initialData: "" });
    await flush();
    source.value = "b";
    await flush();
    await refresh();
    await flush();
    expect(n).toBe(3);
    expect(data.value).toBe("run-3");
  });
});
