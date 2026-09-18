export interface ImageItem {
  id: string;
  relative_path: string;
  original_filename: string | null;
  width: number | null;
  height: number | null;
  has_thumbnail: boolean;
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
  song_id?: string | null;
  song_id_candidates?: Candidate[];
  partner_id?: string | null;
  partner_id_candidates?: Candidate[];
}

export type ResultFields = Omit<DeviceResult, "image_id" | "updated_at">;

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
export const CLEAR_STATUS_NAMES = ["Track Lost", "Track Complete", "FULL RECALL", "PURE MEMORY"];

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

export const catalog = {
  songs: (): Promise<SongEntry[]> => {
    catalogCache.songs ??= request<SongEntry[]>("/api/catalog/songs");
    return catalogCache.songs as Promise<SongEntry[]>;
  },
  partners: (): Promise<PartnerEntry[]> => {
    catalogCache.partners ??= request<PartnerEntry[]>("/api/catalog/partners");
    return catalogCache.partners as Promise<PartnerEntry[]>;
  },
  partnerIconUrl: (id: string) => `/api/catalog/partners/${id}/icon`,
};

export const api = {
  listImages: (uncheckedOnly: boolean, offset: number, limit: number) =>
    request<{ total: number; items: ImageItem[] }>(
      `/api/images?unchecked_only=${uncheckedOnly}&offset=${offset}&limit=${limit}`,
    ),
  getPrefill: (id: string) => request<Prefill>(`/api/images/${id}/prefill`),
  getResult: (id: string) => request<DeviceResult>(`/api/images/${id}/result`),
  saveResult: (id: string, fields: ResultFields) =>
    request<DeviceResult>(`/api/images/${id}/result`, {
      method: "PUT",
      body: JSON.stringify(fields),
    }),
  createImport: (sourcePath: string, recursive: boolean) =>
    request<ImportBatch>("/api/imports", {
      method: "POST",
      body: JSON.stringify({ source_path: sourcePath, recursive }),
    }),
  listImports: () => request<ImportBatch[]>("/api/imports"),
  thumbUrl: (id: string) => `/api/images/${id}/thumb`,
  fileUrl: (id: string) => `/api/images/${id}/file`,
};
