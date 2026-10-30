<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { toast } from "vue-sonner";
import {
  api,
  catalog,
  CLEAR_STATUS_NAMES,
  RATING_CLASS_NAMES,
  type DeviceResult,
  type DeviceRois,
  type PartnerEntry,
  type Prefill,
  type ResultFields,
  type SongEntry,
} from "@/api";
import B30Annotate from "@/features/annotate/components/B30Annotate.vue";
import Button from "@/components/ui/Button.vue";
import CheckedToggle from "@/components/ui/CheckedToggle.vue";
import ConfirmDialog from "@/components/ui/ConfirmDialog.vue";
import FlowSelector from "@/features/annotate/components/FlowSelector.vue";
import ImageViewer from "@/features/annotate/components/ImageViewer.vue";
import LoadingMask from "@/components/ui/LoadingMask.vue";
import NumberField from "@/components/ui/NumberField.vue";
import PartnerPicker from "@/features/annotate/components/PartnerPicker.vue";
import RoiCrop from "@/features/annotate/components/RoiCrop.vue";
import SegmentedSelect from "@/components/ui/SegmentedSelect.vue";
import SongPicker from "@/features/annotate/components/SongPicker.vue";
import type { FieldCrop } from "@/features/annotate/lib/roiCropStyle";
import { computeWarnings, voteHint } from "@/features/annotate/lib/warnings";
import { mergeFields } from "@/features/annotate/lib/mergeFields";
import { useAnnotateActions } from "@/features/annotate/lib/useAnnotateActions";
import { useGuardedAction } from "@/features/annotate/lib/useGuardedAction";
import { prefilledKeys, useFieldSources } from "@/composables/useFieldSources";
import { useRequest } from "@/composables/useRequest";

const route = useRoute();

const imageId = computed(() => String(route.params.id));
const imgReady = ref(false);
const viewerOpen = ref(false);
// the main image displays the black-edge-cropped copy (the ROI geometry's
// coordinate system). /file takes over when that copy fails to load
const usingFallback = ref(false);

interface AnnotateData {
  prefill: Prefill | null;
  b30Layout: string | null;
  saved: DeviceResult | null;
  filename: string | null;
  songs: SongEntry[];
  partners: PartnerEntry[];
  imageKind: string | null;
  b30CheckedCount: number | null;
}

const emptyFields = (): ResultFields => ({
  rois_type: null,
  song_id: null,
  partner_id: null,
  rating_class: null,
  clear_status: null,
  score: null,
  pure: null,
  far: null,
  lost: null,
  max_recall: null,
  high_score: null,
  high_score_delta: null,
  pure_shiny: null,
  pure_early: null,
  pure_late: null,
  far_early: null,
  far_late: null,
  checked: false,
});

const { form, prefilled, markPrefilled } = useFieldSources(reactive<ResultFields>(emptyFields()));

const roisTypeOptions = [
  { value: null, label: "未知" },
  { value: 0, label: "T1" },
  { value: 1, label: "T2" },
];
const ratingClassOptions = RATING_CLASS_NAMES.map((label, i) => ({ value: i, label }));
// device screenshots never render easy/hard clear
const clearStatusOptions = CLEAR_STATUS_NAMES.slice(0, 4).map((label, i) => ({
  value: i,
  label,
}));

const { data, loading } = useRequest(
  imageId,
  async (id): Promise<AnnotateData> => {
    const [prefillResponse, saved, image, songs, partners] = await Promise.all([
      api.getPrefill(id).catch((e: Error) => {
        toast.error(`预识别失败：${e.message}`);
        return null;
      }),
      api.getResult(id).catch(() => null),
      api.getImage(id).catch(() => null),
      catalog.songs().catch(() => [] as SongEntry[]),
      catalog.partners().catch(() => [] as PartnerEntry[]),
    ]);
    return {
      prefill: prefillResponse?.kind === "device" ? prefillResponse.prefill : null,
      b30Layout: prefillResponse?.kind === "b30" ? prefillResponse.layout : null,
      saved,
      filename: image?.original_filename ?? null,
      songs,
      partners,
      imageKind: image?.kind ?? null,
      b30CheckedCount: image?.b30_checked_count ?? null,
    };
  },
  {
    initialData: {
      prefill: null,
      b30Layout: null,
      saved: null,
      filename: null,
      songs: [],
      partners: [],
      imageKind: null,
      b30CheckedCount: null,
    },
  },
);

const { busyAction, withBusy, goNext, skip, hideAndNext } = useAnnotateActions<
  "saveChecked" | "saveAndNext"
>(imageId, "device", () => loading.value);

// saving a device annotation on a B30-classified image deletes its B30
// rows (one kind per image); the first such save needs a confirmation
const {
  pending: crossKindPending,
  run: runCrossKindGuarded,
  confirm: confirmCrossKind,
  cancel: cancelCrossKind,
} = useGuardedAction(() => data.value.imageKind === "b30", imageId);

const crossKindWarning = computed(() => {
  const checked = data.value.b30CheckedCount ?? 0;
  const cards = checked > 0 ? `（已确认 ${checked} 张卡）` : "";
  return `该图已按 B30/50 标注${cards}。保存 device 标注将删除其全部 B30 数据，此图改按 device 结果处理。`;
});

// the flow switch is ephemeral UI state seeded by the probe (never
// persisted; queue kind derives from saved rows)
const flowOverride = ref<"device" | "b30" | null>(null);
const devicePrefillFetched = ref(false);
const prefillLoading = ref(false);
const flow = computed<"device" | "b30">(
  () => flowOverride.value ?? (data.value?.b30Layout != null ? "b30" : "device"),
);

async function onFlowChange(value: "device" | "b30") {
  flowOverride.value = value;
  if (value === "device") void fetchDevicePrefill();
}

// /prefill dispatches on the probe, so a b30-probed image viewed as
// device needs flow=device to get the device OCR proposal
async function fetchDevicePrefill() {
  if (devicePrefillFetched.value || data.value?.prefill != null) return;
  devicePrefillFetched.value = true;
  const id = imageId.value;
  prefillLoading.value = true;
  try {
    const res = await api.getPrefill(id, "device");
    // navigation while the request ran would target a different image
    if (id !== imageId.value) return;
    const prefill = res.kind === "device" ? res.prefill : null;
    if (data.value != null) data.value = { ...data.value, prefill };
    if (prefill != null) fillEmptyFromPrefill(prefill);
  } catch (e) {
    toast.error(`预识别失败：${(e as Error).message}`);
  } finally {
    prefillLoading.value = false;
  }
}

// a saved draft or in-progress edits win; prefill fills null fields only
function fillEmptyFromPrefill(prefill: Prefill) {
  const candidates: [keyof ResultFields, number | string | null | undefined][] = [
    ["rois_type", prefill.rois_type],
    ["song_id", prefill.song_id],
    ["partner_id", prefill.partner_id],
    ["rating_class", prefill.rating_class],
    ["clear_status", prefill.clear_status],
    ["score", prefill.score],
    ["pure", prefill.pure],
    ["far", prefill.far],
    ["lost", prefill.lost],
    ["max_recall", prefill.max_recall],
    ["high_score", prefill.high_score],
    ["high_score_delta", prefill.high_score_delta],
    ["pure_shiny", prefill.pure_shiny],
    ["pure_early", prefill.pure_early],
    ["pure_late", prefill.pure_late],
    ["far_early", prefill.far_early],
    ["far_late", prefill.far_late],
  ];
  const filled: (keyof ResultFields)[] = [];
  for (const [key, value] of candidates) {
    const current = form[key];
    if (value != null && current == null) {
      // union-keyed writes demand an intersection of every field's type
      (form as Record<string, unknown>)[key] = value;
      filled.push(key);
    }
  }
  for (const key of filled) prefilled.add(key);
}

const songs = computed(() => data.value.songs);
const partners = computed(() => data.value.partners);
const filename = computed(() => data.value.filename);
const songCandidates = computed(() => data.value.prefill?.song_id_candidates ?? []);
const partnerCandidates = computed(() => data.value.prefill?.partner_id_candidates ?? []);

watch(
  data,
  (loaded) => {
    // saved (draft) values win, but empty fields fall back to prefill
    Object.assign(form, mergeFields(emptyFields(), loaded.prefill, loaded.saved));
    markPrefilled(
      prefilledKeys(
        Object.keys(emptyFields()) as (keyof ResultFields)[],
        loaded.saved,
        loaded.prefill,
      ),
    );
    void preloadNext();
  },
  { immediate: true },
);

watch(imageId, () => {
  imgReady.value = false;
  viewerOpen.value = false;
  flowOverride.value = null;
  devicePrefillFetched.value = false;
  usingFallback.value = false;
});

const ratingHint = computed(() => voteHint(data.value.prefill?.rating_class_votes));
const clearHint = computed(() => voteHint(data.value.prefill?.clear_status_votes));

// field windows on the cropped image, refetched whenever rois_type
// changes. null while unknown or undetectable - the form annotates
// fine without crops
const deviceRois = ref<DeviceRois | null>(null);

watch([imageId, () => form.rois_type], async ([id, roisType]) => {
  deviceRois.value = null;
  if (roisType == null) return;
  try {
    const rois = await api.getDeviceRois(id, roisType);
    if (id === imageId.value) deviceRois.value = rois;
  } catch {
    // no crops for this image - not an annotation-blocking failure
  }
});

const crops = computed<Record<string, FieldCrop | undefined>>(() => {
  const rois = deviceRois.value;
  // rects are coordinates on the cropped image. On the /file fallback
  // the coordinate system no longer matches, so crops must go dark
  if (rois == null || usingFallback.value) return {};
  const src = api.croppedUrl(imageId.value);
  const crop = (rect: DeviceRois["rects"][string]): FieldCrop => ({
    src,
    rect,
    canvas: rois.canvas,
  });
  const rects = rois.rects;
  return {
    score: crop(rects.score),
    pure: crop(rects.pure),
    far: crop(rects.far),
    lost: crop(rects.lost),
    max_recall: crop(rects.max_recall),
    pure_shiny: crop(rects.pure_shiny),
    high_score: crop(rects.high_score),
    high_score_delta: crop(rects.high_score_delta),
    rating_class: crop(rects.rating_class),
    clear_status: crop(rects.clear_status),
    // one strip for all four early/late inputs, rendered above their grid
    early_late: crop(rects.early_late),
  };
});

async function preloadNext() {
  try {
    const { id: nextId } = await api.getNextImage(imageId.value);
    if (nextId != null && nextId !== imageId.value) {
      new Image().src = api.croppedUrl(nextId);
    }
  } catch {
    // preload is best-effort
  }
}

async function save(): Promise<boolean> {
  try {
    const saved = await api.saveResult(imageId.value, { ...form });
    form.checked = saved.checked;
    return true;
  } catch (e) {
    toast.error(`保存失败：${(e as Error).message}`);
    return false;
  }
}

function saveAndNext() {
  // the form holds the previous image's values until the load lands
  if (loading.value) return;
  runCrossKindGuarded(() => void doSaveAndNext());
}

function saveChecked() {
  if (loading.value) return;
  runCrossKindGuarded(() => void doSaveChecked());
}

function doSaveAndNext(): Promise<void> {
  return withBusy("saveAndNext", async () => {
    if (await save()) await goNext();
  });
}

function doSaveChecked(): Promise<void> {
  form.checked = true;
  return withBusy("saveChecked", async () => {
    if (await save()) await goNext();
  });
}

const warnings = computed(() => computeWarnings(form));

function onKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === "Enter") {
    saveAndNext();
  }
  if (event.key === "Escape") {
    viewerOpen.value = false;
  }
}

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
});
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <B30Annotate v-if="flow === 'b30'" :flow="flow" @switch="onFlowChange" />
  <!-- the form stays mounted under the mask: picker inputs sync through
       modelValue watches that a mount/unmount swap would bypass -->
  <div v-else class="relative grid gap-4 py-4 lg:grid-cols-[1fr_360px]">
    <section
      class="sticky top-0 z-10 self-start bg-background pb-1 lg:top-4 lg:z-0 lg:bg-transparent lg:pb-0"
    >
      <FlowSelector :flow="flow" @switch="onFlowChange" />
      <div class="relative mt-2 overflow-hidden rounded border border-border bg-card">
        <img
          :src="usingFallback ? api.fileUrl(imageId) : api.croppedUrl(imageId)"
          class="mx-auto block max-w-full cursor-zoom-in lg:max-h-[calc(100dvh-6rem)] lg:object-contain"
          :alt="filename ?? imageId"
          @load="imgReady = true"
          @error="usingFallback = true"
          @click="viewerOpen = true"
        />
        <div
          v-if="!imgReady"
          class="absolute inset-0 grid place-items-center rounded border border-border bg-card text-muted-foreground"
        >
          <i class="i-lucide-loader-circle size-6 animate-spin" />
        </div>
      </div>
      <!-- break-all: imported filenames are one long unbreakable token
           that would otherwise widen the page -->
      <div class="mt-1 flex items-center justify-between gap-2">
        <p class="break-all text-xs text-muted-foreground">{{ filename ?? imageId }}</p>
        <Button
          variant="secondary"
          class="shrink-0 text-xs"
          :disabled="busyAction !== null"
          @click="hideAndNext"
        >
          <i
            :class="
              busyAction === 'hide'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-eye-off size-4'
            "
          />
          隐藏并下一张
        </Button>
      </div>
    </section>

    <section class="space-y-4">
      <div class="relative rounded border border-border bg-card p-3 space-y-3">
        <SegmentedSelect
          v-model="form.rois_type"
          label="rois_type"
          :options="roisTypeOptions"
          :prefilled="prefilled.has('rois_type')"
        />

        <PartnerPicker
          v-model="form.partner_id"
          :candidates="partnerCandidates"
          :partners="partners"
          :prefilled="prefilled.has('partner_id')"
        />

        <SegmentedSelect
          v-model="form.rating_class"
          label="rating_class"
          :options="ratingClassOptions"
          :hint="ratingHint"
          :prefilled="prefilled.has('rating_class')"
        >
          <template #crop>
            <RoiCrop v-if="crops.rating_class" v-bind="crops.rating_class" class="mt-1" />
          </template>
        </SegmentedSelect>

        <NumberField
          v-model="form.max_recall"
          label="max_recall"
          :prefilled="prefilled.has('max_recall')"
        >
          <template #crop>
            <RoiCrop v-if="crops.max_recall" v-bind="crops.max_recall" class="mt-0.5" />
          </template>
        </NumberField>

        <SongPicker
          v-model="form.song_id"
          :candidates="songCandidates"
          :songs="songs"
          :prefilled="prefilled.has('song_id')"
        />

        <SegmentedSelect
          v-model="form.clear_status"
          label="clear_status"
          :options="clearStatusOptions"
          :hint="clearHint"
          :prefilled="prefilled.has('clear_status')"
        >
          <template #crop>
            <RoiCrop v-if="crops.clear_status" v-bind="crops.clear_status" class="mt-1" />
          </template>
        </SegmentedSelect>

        <NumberField v-model="form.score" label="score" :prefilled="prefilled.has('score')">
          <template #crop>
            <RoiCrop v-if="crops.score" v-bind="crops.score" class="mt-0.5" />
          </template>
        </NumberField>

        <div class="grid grid-cols-2 gap-2">
          <NumberField
            v-model="form.high_score"
            label="high_score"
            :prefilled="prefilled.has('high_score')"
          >
            <template #crop>
              <RoiCrop v-if="crops.high_score" v-bind="crops.high_score" class="mt-0.5" />
            </template>
          </NumberField>
          <NumberField
            v-model="form.high_score_delta"
            label="high_score_delta"
            :prefilled="prefilled.has('high_score_delta')"
          >
            <template #crop>
              <RoiCrop
                v-if="crops.high_score_delta"
                v-bind="crops.high_score_delta"
                class="mt-0.5"
              />
            </template>
          </NumberField>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <NumberField v-model="form.pure" label="pure" :prefilled="prefilled.has('pure')">
            <template #crop>
              <RoiCrop v-if="crops.pure" v-bind="crops.pure" class="mt-0.5" />
            </template>
          </NumberField>
          <NumberField
            v-model="form.pure_shiny"
            label="pure_shiny"
            :prefilled="prefilled.has('pure_shiny')"
          >
            <template #crop>
              <RoiCrop v-if="crops.pure_shiny" v-bind="crops.pure_shiny" class="mt-0.5" />
            </template>
          </NumberField>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <NumberField v-model="form.far" label="far" :prefilled="prefilled.has('far')">
            <template #crop>
              <RoiCrop v-if="crops.far" v-bind="crops.far" class="mt-0.5" />
            </template>
          </NumberField>
          <NumberField v-model="form.lost" label="lost" :prefilled="prefilled.has('lost')">
            <template #crop>
              <RoiCrop v-if="crops.lost" v-bind="crops.lost" class="mt-0.5" />
            </template>
          </NumberField>
        </div>

        <RoiCrop v-if="crops.early_late" v-bind="crops.early_late" />

        <div class="grid grid-cols-4 gap-2">
          <NumberField
            v-model="form.far_late"
            label="far_late"
            :prefilled="prefilled.has('far_late')"
          />
          <NumberField
            v-model="form.pure_late"
            label="pure_late"
            :prefilled="prefilled.has('pure_late')"
          />
          <NumberField
            v-model="form.far_early"
            label="far_early"
            :prefilled="prefilled.has('far_early')"
          />
          <NumberField
            v-model="form.pure_early"
            label="pure_early"
            :prefilled="prefilled.has('pure_early')"
          />
        </div>

        <CheckedToggle v-model="form.checked" class="mt-1" />

        <LoadingMask v-if="prefillLoading" tone="card" size="size-5" />
      </div>

      <div
        v-if="warnings.length > 0"
        class="rounded border border-destructive-border bg-destructive-soft p-3 text-sm text-destructive"
      >
        <div class="mb-1 flex items-center gap-1.5 font-medium">
          <i class="i-lucide-triangle-alert size-4" />
          一致性警告
        </div>
        <ul class="list-inside list-disc space-y-0.5">
          <li v-for="w in warnings" :key="w">{{ w }}</li>
        </ul>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <Button :disabled="busyAction !== null" @click="saveChecked">
          <i
            :class="
              busyAction === 'saveChecked'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-check size-4'
            "
          />
          确认并下一张
        </Button>
        <Button variant="secondary" :disabled="busyAction !== null" @click="saveAndNext">
          <i
            :class="
              busyAction === 'saveAndNext'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-save size-4'
            "
          />
          保存草稿并下一张
        </Button>
        <Button variant="secondary" :disabled="busyAction !== null" @click="skip">
          <i
            :class="
              busyAction === 'skip'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-skip-forward size-4'
            "
          />
          跳过
        </Button>
      </div>
    </section>

    <LoadingMask v-if="loading" tone="page" />

    <ImageViewer
      :open="viewerOpen"
      :src="api.fileUrl(imageId)"
      :label="filename ?? imageId"
      :alt="filename ?? imageId"
      @close="viewerOpen = false"
    />

    <ConfirmDialog
      :open="crossKindPending"
      title="保存 device 标注"
      :description="crossKindWarning"
      confirm-label="保存并删除 B30 数据"
      destructive
      @update:open="
        (open: boolean) => {
          if (!open) cancelCrossKind();
        }
      "
      @confirm="confirmCrossKind"
    />
  </div>
</template>
