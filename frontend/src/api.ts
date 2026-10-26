import type { components } from "./api-schema";

type Schemas = components["schemas"];

/**
 * A stored screenshot. `checked` is null when not annotated yet; on b30
 * images it is the derived "every expected component checked" state and
 * `b30_checked_count` / `b30_component_count` carry its per-card
 * progress (the count is null when the layout is unknown). Hidden
 * images stay dedup anchors but appear in no queue.
 */
export type ImageItem = Schemas["ImageOut"];

export type ImportBatch = Schemas["ImportBatchOut"];

export type Candidate = Schemas["PrefillCandidate"];

export type Prefill = Schemas["PrefillPayload"];

// saved results always serialize every field; the schema keeps them
// optional only because the same model doubles as the partial PUT body
export type DeviceResult = Required<Schemas["DeviceResultOut"]>;

export type ResultFields = Omit<DeviceResult, "image_id" | "updated_at">;

// as with DeviceResult: saved components always carry every field
export type B30ComponentFields = Required<Schemas["B30ComponentIn"]>;

export type B30Result = Omit<Schemas["B30ResultOut"], "components"> & {
  components: B30ComponentFields[];
};

// the card OCR pass always emits every field
export type B30ComponentPrefill = Required<Schemas["B30ComponentPrefillOut"]>;

// GET /{id}/prefill serializes with exclude_unset: the b30 variant
// carries only `layout`, the device variant only `prefill` — a presence
// split the schema cannot express, so the union is stated here
export type PrefillResponse =
  | { kind: "b30"; layout: string }
  | { kind: "device"; prefill: Prefill };

export type B30LayoutInfo = Schemas["B30LayoutOut"];

export type QueueKind = ImageItem["kind"];

export type SongEntry = Schemas["SongOut"];

/** Partner letter id and display name; `name` is null when the game's
 * characters file has no entry for the id. */
export type PartnerEntry = Schemas["PartnerOut"];

export const RATING_CLASS_NAMES = ["PST", "PRS", "FTR", "BYD", "ETR"];
export const CLEAR_STATUS_NAMES = ["TL", "TC", "FR", "PM", "EC", "HC"];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? res.statusText);
  }
  return res.json();
}

const catalogCache: Record<"songs" | "partners", Promise<unknown> | null> = {
  songs: null,
  partners: null,
};

function cachedCatalog<T>(key: "songs" | "partners", path: string): Promise<T> {
  // a failed fetch is not memoized, so the next call retries
  catalogCache[key] ??= request<T>(path).catch((e: Error) => {
    catalogCache[key] = null;
    throw e;
  });
  return catalogCache[key] as Promise<T>;
}

export const catalog = {
  songs: () => cachedCatalog<SongEntry[]>("songs", "/api/catalog/songs"),
  partners: () => cachedCatalog<PartnerEntry[]>("partners", "/api/catalog/partners"),
  partnerIconUrl: (id: string) => `/api/catalog/partners/${id}/icon`,
};

export const api = {
  listImages: (
    uncheckedOnly: boolean,
    offset: number,
    limit: number,
    kind: QueueKind | null = null,
    hiddenOnly = false,
  ) =>
    request<Schemas["ImageListOut"]>(
      `/api/images?unchecked_only=${uncheckedOnly}&offset=${offset}&limit=${limit}${kind ? `&kind=${kind}` : ""}${hiddenOnly ? "&hidden=only" : ""}`,
    ),
  getImage: (id: string) => request<ImageItem>(`/api/images/${id}`),
  // reversible and idempotent
  setImageHidden: (id: string, hidden: boolean) =>
    request<ImageItem>(`/api/images/${id}/hidden`, {
      method: "PUT",
      body: JSON.stringify({ hidden }),
    }),
  // null id = no unchecked image left
  getNextImage: (id: string, kind: QueueKind = "device") =>
    request<{ id: string | null }>(`/api/images/${id}/next?kind=${kind}`),
  // flow=device forces the device proposal even for b30-probed images
  getPrefill: (id: string, flow?: "device") =>
    request<PrefillResponse>(`/api/images/${id}/prefill${flow ? `?flow=${flow}` : ""}`),
  getResult: (id: string) =>
    // null = not annotated yet
    request<DeviceResult | null>(`/api/images/${id}/result`),
  saveResult: (id: string, fields: ResultFields) =>
    request<DeviceResult>(`/api/images/${id}/result`, {
      method: "PUT",
      body: JSON.stringify(fields),
    }),
  getB30Result: (id: string) =>
    // null = not annotated yet
    request<B30Result | null>(`/api/images/${id}/b30_result`),
  // upserts the given components only; others stay untouched
  saveB30Result: (id: string, layout: string | null, components: B30ComponentFields[]) =>
    request<B30Result>(`/api/images/${id}/b30_result`, {
      method: "PUT",
      body: JSON.stringify({ layout, components }),
    }),
  // layout overrides the backend's probed layout when given
  getB30ComponentPrefill: (id: string, index: number, layout?: string) =>
    request<B30ComponentPrefill>(
      `/api/images/${id}/b30_prefill/${index}${layout ? `?layout=${layout}` : ""}`,
    ),
  b30CardUrl: (id: string, index: number, layout?: string) =>
    `/api/images/${id}/b30_card/${index}${layout ? `?layout=${layout}` : ""}`,
  getB30Layouts: () => request<B30LayoutInfo[]>("/api/images/b30_layouts"),
  createImport: (sourcePath: string, recursive: boolean) =>
    request<ImportBatch>("/api/imports", {
      method: "POST",
      body: JSON.stringify({ source_path: sourcePath, recursive }),
    }),
  listImports: () => request<ImportBatch[]>("/api/imports"),
  thumbUrl: (id: string) => `/api/images/${id}/thumb`,
  fileUrl: (id: string) => `/api/images/${id}/file`,
};
