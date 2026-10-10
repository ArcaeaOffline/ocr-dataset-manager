export interface ImageItem {
  id: string;
  relative_path: string;
  original_filename: string | null;
  width: number | null;
  height: number | null;
  // "device" | "b30" | "unclassified"; for b30 images `checked` carries
  // the derived "every component checked" state
  kind: string;
  checked: boolean | null;
  created_at: string;
}

export interface ImportBatch {
  id: string;
  source_path: string;
  started_at: string;
  finished_at: string | null;
  file_count: number;
  imported_count: number;
  skipped_count: number;
  failed_count: number;
}

export interface Candidate {
  image_id: string;
  confidence: number;
}

export interface Prefill {
  rois_type: number | null;
  score?: number | null;
  pure?: number | null;
  far?: number | null;
  lost?: number | null;
  max_recall?: number | null;
  rating_class?: number | null;
  rating_class_votes?: number[];
  clear_status?: number | null;
  clear_status_votes?: number[];
  high_score?: number | null;
  high_score_delta?: number | null;
  pure_shiny?: number | null;
  pure_early?: number | null;
  pure_late?: number | null;
  far_early?: number | null;
  far_late?: number | null;
  song_id?: string | null;
  song_id_candidates?: Candidate[];
  partner_id?: string | null;
  partner_id_candidates?: Candidate[];
}

export type ResultFields = Omit<DeviceResult, "image_id" | "updated_at">;

export interface B30ComponentFields {
  index: number;
  song_id: string | null;
  rating_class: number | null;
  score: number | null;
  pure: number | null;
  far: number | null;
  lost: number | null;
  pure_shiny: number | null;
  clear_status: number | null;
  checked: boolean;
}

export interface B30Result {
  layout: string | null;
  components: B30ComponentFields[];
  updated_at: string;
}

export interface B30ComponentPrefill {
  index: number;
  song_id: string | null;
  song_id_candidates: Candidate[];
  rating_class: number | null;
  rating_class_votes: number[] | null;
  score: number | null;
  pure: number | null;
  far: number | null;
  lost: number | null;
  pure_shiny: number | null;
  clear_status: number | null;
}

// GET /{id}/prefill dispatches on the probed renderer
export type PrefillResponse =
  | { kind: "b30"; layout: string }
  | { kind: "device"; prefill: Prefill };

export interface B30LayoutInfo {
  id: string;
  component_count: number;
}

export interface DeviceResult {
  image_id: string;
  rois_type: number | null;
  song_id: string | null;
  partner_id: string | null;
  rating_class: number | null;
  clear_status: number | null;
  score: number | null;
  pure: number | null;
  far: number | null;
  lost: number | null;
  max_recall: number | null;
  high_score: number | null;
  high_score_delta: number | null;
  pure_shiny: number | null;
  pure_early: number | null;
  pure_late: number | null;
  far_early: number | null;
  far_late: number | null;
  checked: boolean;
  updated_at: string;
}

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

export interface SongEntry {
  id: string;
  title: string;
}

export interface PartnerEntry {
  id: string;
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

export type QueueKind = "device" | "b30" | "unclassified";

export const api = {
  listImages: (
    uncheckedOnly: boolean,
    offset: number,
    limit: number,
    kind: QueueKind | null = null,
  ) =>
    request<{ total: number; items: ImageItem[] }>(
      `/api/images?unchecked_only=${uncheckedOnly}&offset=${offset}&limit=${limit}${kind ? `&kind=${kind}` : ""}`,
    ),
  getImage: (id: string) => request<ImageItem>(`/api/images/${id}`),
  // null id = no unchecked image left
  getNextImage: (id: string, kind: QueueKind = "device") =>
    request<{ id: string | null }>(`/api/images/${id}/next?kind=${kind}`),
  getPrefill: (id: string) => request<PrefillResponse>(`/api/images/${id}/prefill`),
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
  getB30ComponentPrefill: (id: string, index: number) =>
    request<B30ComponentPrefill>(`/api/images/${id}/b30_prefill/${index}`),
  b30CardUrl: (id: string, index: number) => `/api/images/${id}/b30_card/${index}`,
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
