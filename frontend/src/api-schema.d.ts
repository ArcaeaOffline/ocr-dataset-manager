export interface paths {
  "/api/imports": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Imports */
    get: operations["listImports"];
    put?: never;
    /** Create Import */
    post: operations["createImport"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/imports/{batch_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Import */
    get: operations["getImport"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * List Images
     * @description `hidden` absent: exclude hidden images; `hidden=only`: list only
     *     hidden ones.
     */
    get: operations["listImages"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/b30_layouts": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * List B30 Layouts
     * @description Layout ids with their expected card counts, for the annotate UI.
     */
    get: operations["listB30Layouts"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Image */
    get: operations["getImage"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/hidden": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /**
     * Set Image Hidden
     * @description Hiding is reversible and idempotent; the row stays as a sha256
     *     dedup anchor, so re-importing the same file still counts as skipped.
     */
    put: operations["setImageHidden"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/next": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * Get Next Unchecked
     * @description Next unchecked image in queue order (newest first), starting after
     *     `image_id` and wrapping to the queue head; `{"id": None}` when no
     *     unchecked image remains.
     */
    get: operations["getNextUnchecked"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/prefill": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * Get Prefill
     * @description Prefill for whichever flow the image probes as: the B30 layout id
     *     when it matches a B30 rendering, else the device OCR proposal.
     *     `flow=device` skips the probe and computes the device OCR proposal
     *     even for b30-probed images.
     */
    get: operations["getPrefill"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/b30_prefill/{component_index}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * Get B30 Component Prefill
     * @description OCR proposal for one card; 422 when the image does not probe as a
     *     supported B30 layout. `layout` overrides the probed layout.
     */
    get: operations["getB30ComponentPrefill"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/b30_card/{component_index}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get B30 Card */
    get: operations["getB30Card"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/b30_result": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * Get B30 Result
     * @description Saved B30 annotation; `None` (HTTP 200) means not annotated yet.
     */
    get: operations["getB30Result"];
    /** Save B30 Result */
    put: operations["saveB30Result"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/result": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * Get Result
     * @description Saved annotation; `None` (HTTP 200) means not annotated yet.
     */
    get: operations["getResult"];
    /** Save Result */
    put: operations["saveResult"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/thumb": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Thumbnail */
    get: operations["getThumbnail"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/images/{image_id}/file": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Original */
    get: operations["getOriginal"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/catalog/songs": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Songs */
    get: operations["listSongs"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/catalog/partners": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Partners */
    get: operations["listPartners"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/catalog/partners/{partner_id}/icon": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Partner Icon */
    get: operations["partnerIcon"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/health": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Health */
    get: operations["health"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** B30ComponentIn */
    B30ComponentIn: {
      /** Index */
      index: number;
      /** Song Id */
      song_id?: string | null;
      /** Rating Class */
      rating_class?: number | null;
      /** Score */
      score?: number | null;
      /** Pure */
      pure?: number | null;
      /** Far */
      far?: number | null;
      /** Lost */
      lost?: number | null;
      /** Pure Shiny */
      pure_shiny?: number | null;
      /** Clear Status */
      clear_status?: number | null;
      /**
       * Checked
       * @default false
       */
      checked: boolean;
    };
    /** B30ComponentPrefillOut */
    B30ComponentPrefillOut: {
      /** Index */
      index: number;
      /** Song Id */
      song_id?: string | null;
      /**
       * Song Id Candidates
       * @default []
       */
      song_id_candidates: components["schemas"]["PrefillCandidate"][];
      /** Rating Class */
      rating_class?: number | null;
      /** Rating Class Votes */
      rating_class_votes?: number[] | null;
      /** Score */
      score?: number | null;
      /** Pure */
      pure?: number | null;
      /** Far */
      far?: number | null;
      /** Lost */
      lost?: number | null;
      /** Pure Shiny */
      pure_shiny?: number | null;
      /** Clear Status */
      clear_status?: number | null;
    };
    /** B30LayoutOut */
    B30LayoutOut: {
      /** Id */
      id: string;
      /** Component Count */
      component_count: number;
    };
    /** B30ResultIn */
    B30ResultIn: {
      /** Layout */
      layout?: string | null;
      /**
       * Components
       * @default []
       */
      components: components["schemas"]["B30ComponentIn"][];
    };
    /** B30ResultOut */
    B30ResultOut: {
      /** Layout */
      layout: string | null;
      /** Components */
      components: components["schemas"]["B30ComponentIn"][];
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /** DeviceResultIn */
    DeviceResultIn: {
      /** Rois Type */
      rois_type?: number | null;
      /** Song Id */
      song_id?: string | null;
      /** Partner Id */
      partner_id?: string | null;
      /** Rating Class */
      rating_class?: number | null;
      /** Clear Status */
      clear_status?: number | null;
      /** Score */
      score?: number | null;
      /** Pure */
      pure?: number | null;
      /** Far */
      far?: number | null;
      /** Lost */
      lost?: number | null;
      /** Max Recall */
      max_recall?: number | null;
      /** High Score */
      high_score?: number | null;
      /** High Score Delta */
      high_score_delta?: number | null;
      /** Pure Shiny */
      pure_shiny?: number | null;
      /** Pure Early */
      pure_early?: number | null;
      /** Pure Late */
      pure_late?: number | null;
      /** Far Early */
      far_early?: number | null;
      /** Far Late */
      far_late?: number | null;
      /**
       * Checked
       * @default false
       */
      checked: boolean;
    };
    /** DeviceResultOut */
    DeviceResultOut: {
      /** Rois Type */
      rois_type?: number | null;
      /** Song Id */
      song_id?: string | null;
      /** Partner Id */
      partner_id?: string | null;
      /** Rating Class */
      rating_class?: number | null;
      /** Clear Status */
      clear_status?: number | null;
      /** Score */
      score?: number | null;
      /** Pure */
      pure?: number | null;
      /** Far */
      far?: number | null;
      /** Lost */
      lost?: number | null;
      /** Max Recall */
      max_recall?: number | null;
      /** High Score */
      high_score?: number | null;
      /** High Score Delta */
      high_score_delta?: number | null;
      /** Pure Shiny */
      pure_shiny?: number | null;
      /** Pure Early */
      pure_early?: number | null;
      /** Pure Late */
      pure_late?: number | null;
      /** Far Early */
      far_early?: number | null;
      /** Far Late */
      far_late?: number | null;
      /**
       * Checked
       * @default false
       */
      checked: boolean;
      /** Image Id */
      image_id: string;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components["schemas"]["ValidationError"][];
    };
    /** HiddenIn */
    HiddenIn: {
      /** Hidden */
      hidden: boolean;
    };
    /** ImageListOut */
    ImageListOut: {
      /** Total */
      total: number;
      /** Items */
      items: components["schemas"]["ImageOut"][];
    };
    /** ImageOut */
    ImageOut: {
      /** Id */
      id: string;
      /** Relative Path */
      relative_path: string;
      /** Original Filename */
      original_filename: string | null;
      /** Width */
      width: number | null;
      /** Height */
      height: number | null;
      /**
       * Kind
       * @enum {string}
       */
      kind: "device" | "b30" | "unclassified";
      /** Checked */
      checked: boolean | null;
      /** B30 Checked Count */
      b30_checked_count?: number | null;
      /** B30 Component Count */
      b30_component_count?: number | null;
      /** Hidden */
      hidden: boolean;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
    };
    /** ImportBatchOut */
    ImportBatchOut: {
      /** Id */
      id: string;
      /** Source Path */
      source_path: string;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /** Finished At */
      finished_at: string | null;
      /** File Count */
      file_count: number;
      /** Imported Count */
      imported_count: number;
      /** Skipped Count */
      skipped_count: number;
      /** Failed Count */
      failed_count: number;
    };
    /** ImportRequest */
    ImportRequest: {
      /** Source Path */
      source_path: string;
      /**
       * Recursive
       * @default false
       */
      recursive: boolean;
    };
    /** NextImageOut */
    NextImageOut: {
      /** Id */
      id: string | null;
    };
    /** PartnerOut */
    PartnerOut: {
      /** Id */
      id: string;
      /** Name */
      name?: string | null;
    };
    /** PrefillCandidate */
    PrefillCandidate: {
      /** Image Id */
      image_id: string;
      /** Confidence */
      confidence: number;
    };
    /** PrefillOut */
    PrefillOut: {
      /**
       * Kind
       * @enum {string}
       */
      kind: "device" | "b30";
      /** Layout */
      layout?: string | null;
      prefill?: components["schemas"]["PrefillPayload"] | null;
    };
    /** PrefillPayload */
    PrefillPayload: {
      /** Rois Type */
      rois_type: number | null;
      /** Score */
      score?: number | null;
      /** Pure */
      pure?: number | null;
      /** Far */
      far?: number | null;
      /** Lost */
      lost?: number | null;
      /** Max Recall */
      max_recall?: number | null;
      /** Rating Class */
      rating_class?: number | null;
      /** Rating Class Votes */
      rating_class_votes?: number[] | null;
      /** Clear Status */
      clear_status?: number | null;
      /** Clear Status Votes */
      clear_status_votes?: number[] | null;
      /** High Score */
      high_score?: number | null;
      /** High Score Delta */
      high_score_delta?: number | null;
      /** Pure Shiny */
      pure_shiny?: number | null;
      /** Pure Early */
      pure_early?: number | null;
      /** Pure Late */
      pure_late?: number | null;
      /** Far Early */
      far_early?: number | null;
      /** Far Late */
      far_late?: number | null;
      /** Song Id */
      song_id?: string | null;
      /**
       * Song Id Candidates
       * @default []
       */
      song_id_candidates: components["schemas"]["PrefillCandidate"][];
      /** Partner Id */
      partner_id?: string | null;
      /**
       * Partner Id Candidates
       * @default []
       */
      partner_id_candidates: components["schemas"]["PrefillCandidate"][];
    };
    /** SongOut */
    SongOut: {
      /** Id */
      id: string;
      /** Title */
      title: string;
    };
    /** ValidationError */
    ValidationError: {
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
      /** Input */
      input?: unknown;
      /** Context */
      ctx?: Record<string, never>;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  listImports: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImportBatchOut"][];
        };
      };
    };
  };
  createImport: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ImportRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImportBatchOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getImport: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImportBatchOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  listImages: {
    parameters: {
      query?: {
        offset?: number;
        limit?: number;
        unchecked_only?: boolean;
        kind?: ("device" | "b30" | "unclassified") | null;
        hidden?: "only" | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImageListOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  listB30Layouts: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["B30LayoutOut"][];
        };
      };
    };
  };
  getImage: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImageOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  setImageHidden: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["HiddenIn"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImageOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getNextUnchecked: {
    parameters: {
      query?: {
        kind?: "device" | "b30";
      };
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["NextImageOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getPrefill: {
    parameters: {
      query?: {
        flow?: "device" | null;
      };
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PrefillOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getB30ComponentPrefill: {
    parameters: {
      query?: {
        layout?: string | null;
      };
      header?: never;
      path: {
        image_id: string;
        component_index: number;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["B30ComponentPrefillOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getB30Card: {
    parameters: {
      query?: {
        layout?: string | null;
      };
      header?: never;
      path: {
        image_id: string;
        component_index: number;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "image/jpeg": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getB30Result: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["B30ResultOut"] | null;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  saveB30Result: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["B30ResultIn"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["B30ResultOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getResult: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DeviceResultOut"] | null;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  saveResult: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["DeviceResultIn"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DeviceResultOut"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getThumbnail: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "image/jpeg": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  getOriginal: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        image_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "image/*": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  listSongs: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SongOut"][];
        };
      };
    };
  };
  listPartners: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PartnerOut"][];
        };
      };
    };
  };
  partnerIcon: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        partner_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "image/png": unknown;
          "image/jpeg": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  health: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": {
            [key: string]: string;
          };
        };
      };
    };
  };
}
