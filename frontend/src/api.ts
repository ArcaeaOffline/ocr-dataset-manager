import createClient from "openapi-fetch";
import type { components, paths } from "./api-schema";

type Schemas = components["schemas"];

/**
 * A stored screenshot. `checked` is null when not annotated yet. On b30
 * images it is the derived "every expected component checked" state and
 * `b30_checked_count` / `b30_component_count` carry its per-card
 * progress (the count is null when the layout is unknown). Hidden
 * images stay dedup anchors but appear in no queue.
 */
export type ImageItem = Schemas["ImageOut"];

export type ImportBatch = Schemas["ImportBatchOut"];

export type Candidate = Schemas["PrefillCandidate"];

export type Prefill = Schemas["PrefillPayload"];

// saved results always serialize every field. The schema keeps them
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
// carries only `layout`, the device variant only `prefill`. That is a
// presence split the schema cannot express, so the union is stated here
export type PrefillResponse =
  | { kind: "b30"; layout: string }
  | { kind: "device"; prefill: Prefill };

export type B30LayoutInfo = Schemas["B30LayoutOut"];

/** Field windows on the black-edge-cropped image. Rects are rounded
 * exactly like the OCR chain rounds them. */
export type DeviceRois = Schemas["DeviceRoisOut"];

export type QueueKind = ImageItem["kind"];

export type SongEntry = Schemas["SongOut"];

/** Partner letter id and display name. `name` is null when the game's
 * characters file has no entry for the id. */
export type PartnerEntry = Schemas["PartnerOut"];

export const RATING_CLASS_NAMES = ["PST", "PRS", "FTR", "BYD", "ETR"];
export const CLEAR_STATUS_NAMES = ["TL", "TC", "FR", "PM", "EC", "HC"];

const client = createClient<paths>();

// openapi-fetch resolves non-2xx to `error` instead of throwing. This
// restores the throw-on-failure contract useRequest is built on.
// Problem errors carry the explanation in `detail`, bare status
// problems (e.g. unmatched /api paths) omit it.
async function unwrap<T>(
  request: Promise<{
    data?: T;
    error?: { detail?: string | null } | undefined;
    response: Response;
  }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (error) {
    throw new Error(error.detail ?? response.statusText);
  }
  return data as T;
}

const catalogCache: Record<"songs" | "partners", Promise<unknown> | null> = {
  songs: null,
  partners: null,
};

function cachedCatalog<T>(key: "songs" | "partners", fetcher: () => Promise<T>): Promise<T> {
  // a failed fetch is not memoized, so the next call retries
  catalogCache[key] ??= fetcher().catch((e: Error) => {
    catalogCache[key] = null;
    throw e;
  });
  return catalogCache[key] as Promise<T>;
}

export const catalog = {
  songs: () => cachedCatalog("songs", () => unwrap(client.GET("/api/catalog/songs"))),
  partners: () => cachedCatalog("partners", () => unwrap(client.GET("/api/catalog/partners"))),
  partnerIconUrl: (id: string) => `/api/catalog/partners/${id}/icon`,
};

// the assertions restore the narrower runtime aliases: saved records
// always serialize every field (see the Required<> aliases) and
// PrefillResponse's exclude_unset union is narrower than its schema
export const api = {
  listImages: (
    uncheckedOnly: boolean,
    offset: number,
    limit: number,
    kind: QueueKind | null = null,
    hiddenOnly = false,
  ) =>
    unwrap(
      client.GET("/api/images", {
        params: {
          query: {
            unchecked_only: uncheckedOnly,
            offset,
            limit,
            kind: kind ?? undefined,
            hidden: hiddenOnly ? "only" : undefined,
          },
        },
      }),
    ),
  getImage: (id: string) =>
    unwrap(client.GET("/api/images/{image_id}", { params: { path: { image_id: id } } })),
  // reversible and idempotent
  setImageHidden: (id: string, hidden: boolean) =>
    unwrap(
      client.PUT("/api/images/{image_id}/hidden", {
        params: { path: { image_id: id } },
        body: { hidden },
      }),
    ),
  // null id = no unchecked image left
  getNextImage: (id: string, kind: "device" | "b30" = "device") =>
    unwrap(
      client.GET("/api/images/{image_id}/next", {
        params: { path: { image_id: id }, query: { kind } },
      }),
    ),
  // flow=device forces the device proposal even for b30-probed images
  getPrefill: (id: string, flow?: "device") =>
    unwrap(
      client.GET("/api/images/{image_id}/prefill", {
        params: { path: { image_id: id }, query: { flow } },
      }),
    ) as Promise<PrefillResponse>,
  getResult: (id: string) =>
    // null = not annotated yet
    unwrap(
      client.GET("/api/images/{image_id}/result", {
        params: { path: { image_id: id } },
      }),
    ) as Promise<DeviceResult | null>,
  saveResult: (id: string, fields: ResultFields) =>
    unwrap(
      client.PUT("/api/images/{image_id}/result", {
        params: { path: { image_id: id } },
        body: fields,
      }),
    ) as Promise<DeviceResult>,
  getB30Result: (id: string) =>
    // null = not annotated yet
    unwrap(
      client.GET("/api/images/{image_id}/b30_result", {
        params: { path: { image_id: id } },
      }),
    ) as Promise<B30Result | null>,
  // upserts the given components only. Others stay untouched
  saveB30Result: (id: string, layout: string | null, components: B30ComponentFields[]) =>
    unwrap(
      client.PUT("/api/images/{image_id}/b30_result", {
        params: { path: { image_id: id } },
        body: { layout, components },
      }),
    ) as Promise<B30Result>,
  // layout overrides the backend's probed layout when given
  getB30ComponentPrefill: (id: string, index: number, layout?: string) =>
    unwrap(
      client.GET("/api/images/{image_id}/b30_prefill/{component_index}", {
        params: { path: { image_id: id, component_index: index }, query: { layout } },
      }),
    ) as Promise<B30ComponentPrefill>,
  b30CardUrl: (id: string, index: number, layout?: string) =>
    `/api/images/${id}/b30_card/${index}${layout ? `?layout=${layout}` : ""}`,
  getB30Layouts: () => unwrap(client.GET("/api/images/b30_layouts")),
  // rois_type overrides T1/T2 detection. Omitted runs the selector.
  // Readable (openapi-fetch's response mapper) flattens the schema's
  // fixed-length tuples to arrays. The wire data carries the tuples
  getDeviceRois: (id: string, roisType?: number) =>
    unwrap(
      client.GET("/api/images/{image_id}/device_rois", {
        params: { path: { image_id: id }, query: { rois_type: roisType } },
      }),
    ) as Promise<DeviceRois>,
  createImport: (sourcePath: string, recursive: boolean) =>
    unwrap(
      client.POST("/api/imports", {
        body: { source_path: sourcePath, recursive },
      }),
    ),
  listImports: () => unwrap(client.GET("/api/imports")),
  thumbUrl: (id: string) => `/api/images/${id}/thumb`,
  fileUrl: (id: string) => `/api/images/${id}/file`,
  // black-edge-cropped copy of /file. ROI rects are coordinates on it
  croppedUrl: (id: string) => `/api/images/${id}/cropped`,
};
