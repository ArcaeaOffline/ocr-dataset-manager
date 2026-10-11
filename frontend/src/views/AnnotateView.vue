<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import {
  api,
  catalog,
  CLEAR_STATUS_NAMES,
  RATING_CLASS_NAMES,
  type DeviceResult,
  type Prefill,
  type ResultFields,
  type SongEntry,
} from "../api";
import B30Annotate from "../components/B30Annotate.vue";
import CheckedToggle from "../components/CheckedToggle.vue";
import FlowSelector from "../components/FlowSelector.vue";
import ImageViewer from "../components/ImageViewer.vue";
import NumberField from "../components/NumberField.vue";
import PartnerPicker from "../components/PartnerPicker.vue";
import SegmentedSelect from "../components/SegmentedSelect.vue";
import SongPicker from "../components/SongPicker.vue";
import { computeWarnings, voteHint } from "../warnings";
import { useBusy } from "../composables/useBusy";
import { useRequest } from "../composables/useRequest";

const route = useRoute();
const router = useRouter();

const imageId = computed(() => String(route.params.id));
const imgReady = ref(false);
const viewerOpen = ref(false);
const { busyAction, withBusy } = useBusy<"saveChecked" | "saveAndNext" | "skip">();

interface AnnotateData {
  prefill: Prefill | null;
  b30Layout: string | null;
  saved: DeviceResult | null;
  filename: string | null;
  songs: SongEntry[];
  partners: { id: string }[];
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

const form = reactive<ResultFields>(emptyFields());

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

function applyPrefill(prefill: Prefill) {
  form.rois_type = prefill.rois_type;
  form.song_id = prefill.song_id ?? null;
  form.partner_id = prefill.partner_id ?? null;
  form.rating_class = prefill.rating_class ?? null;
  form.clear_status = prefill.clear_status ?? null;
  form.score = prefill.score ?? null;
  form.pure = prefill.pure ?? null;
  form.far = prefill.far ?? null;
  form.lost = prefill.lost ?? null;
  form.max_recall = prefill.max_recall ?? null;
  form.high_score = prefill.high_score ?? null;
  form.high_score_delta = prefill.high_score_delta ?? null;
  form.pure_shiny = prefill.pure_shiny ?? null;
  form.pure_early = prefill.pure_early ?? null;
  form.pure_late = prefill.pure_late ?? null;
  form.far_early = prefill.far_early ?? null;
  form.far_late = prefill.far_late ?? null;
}

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
      catalog.partners().catch(() => [] as { id: string }[]),
    ]);
    return {
      prefill: prefillResponse?.kind === "device" ? prefillResponse.prefill : null,
      b30Layout: prefillResponse?.kind === "b30" ? prefillResponse.layout : null,
      saved,
      filename: image?.original_filename ?? null,
      songs,
      partners,
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
    },
  },
);

// the flow switch is ephemeral UI state seeded by the probe (never
// persisted; queue kind derives from saved rows). Switching to device
// on a b30-probed image has no OCR proposal: /prefill dispatches on
// the probe result.
const flowOverride = ref<"device" | "b30" | null>(null);
const flow = computed<"device" | "b30">(
  () => flowOverride.value ?? (data.value?.b30Layout != null ? "b30" : "device"),
);

const songs = computed(() => data.value.songs);
const partners = computed(() => data.value.partners);
const filename = computed(() => data.value.filename);
const songCandidates = computed(() => data.value.prefill?.song_id_candidates ?? []);
const partnerCandidates = computed(() => data.value.prefill?.partner_id_candidates ?? []);

watch(
  data,
  (loaded) => {
    Object.assign(form, emptyFields());
    if (loaded.prefill != null) applyPrefill(loaded.prefill);
    if (loaded.saved != null) {
      // saved (draft) values win, but empty fields fall back to prefill
      const merged: ResultFields = { ...emptyFields(), ...loaded.prefill };
      for (const key of Object.keys(emptyFields()) as (keyof ResultFields)[]) {
        const value = loaded.saved[key];
        if (value != null) {
          (merged as Record<string, unknown>)[key] = value;
        }
      }
      Object.assign(form, merged);
    }
    void preloadNext();
  },
  { immediate: true },
);

watch(imageId, () => {
  imgReady.value = false;
  viewerOpen.value = false;
  flowOverride.value = null;
});

const ratingHint = computed(() => voteHint(data.value.prefill?.rating_class_votes));
const clearHint = computed(() => voteHint(data.value.prefill?.clear_status_votes));

async function preloadNext() {
  try {
    const { id: nextId } = await api.getNextImage(imageId.value);
    if (nextId != null && nextId !== imageId.value) {
      new Image().src = api.fileUrl(nextId);
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

async function goNext() {
  let nextId: string | null;
  try {
    ({ id: nextId } = await api.getNextImage(imageId.value));
  } catch (e) {
    toast.error(`获取下一张失败：${(e as Error).message}`);
    return;
  }
  if (nextId === null) {
    toast.success("没有未标注的图片了");
    await router.push("/");
    return;
  }
  await router.replace(`/annotate/${nextId}`);
}

async function saveAndNext() {
  await withBusy("saveAndNext", async () => {
    if (await save()) await goNext();
  });
}

async function saveChecked() {
  form.checked = true;
  await withBusy("saveChecked", async () => {
    if (await save()) await goNext();
  });
}

async function skip() {
  await withBusy("skip", goNext);
}

const warnings = computed(() => computeWarnings(form));

function onKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === "Enter") {
    void saveAndNext();
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
  <B30Annotate v-if="flow === 'b30'" :flow="flow" @switch="flowOverride = $event" />
  <div
    v-else-if="loading"
    class="grid place-items-center py-24 text-muted-foreground"
    aria-busy="true"
  >
    <i class="i-lucide-loader-circle size-6 animate-spin" />
  </div>
  <div v-else class="grid gap-4 py-4 lg:grid-cols-[1fr_360px]">
    <section
      class="sticky top-0 z-10 self-start bg-background pb-1 lg:top-4 lg:z-0 lg:bg-transparent lg:pb-0"
    >
      <FlowSelector :flow="flow" @switch="flowOverride = $event" />
      <!-- on mobile, crop to the annotated region (left 3/4, top 11/12 of
           a 16:9 screenshot): ROIs end by ~0.70w/0.90h, the rest of the
           frame is character art; the full frame stays available in the
           viewer -->
      <div
        class="relative mt-2 overflow-hidden rounded border border-border bg-card lt-lg:aspect-[16/11]"
      >
        <img
          :src="api.fileUrl(imageId)"
          class="block w-full max-w-none cursor-zoom-in lt-lg:w-[133.333%] lg:max-h-[calc(100dvh-6rem)] lg:object-contain"
          :alt="filename ?? imageId"
          @load="imgReady = true"
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
      <p class="mt-1 break-all text-xs text-muted-foreground">{{ filename ?? imageId }}</p>
    </section>

    <section class="space-y-4">
      <div class="rounded border border-border bg-card p-3 space-y-3">
        <SegmentedSelect v-model="form.rois_type" label="rois_type" :options="roisTypeOptions" />
        <SegmentedSelect
          v-model="form.rating_class"
          label="rating_class"
          :options="ratingClassOptions"
          :hint="ratingHint"
        />
        <SegmentedSelect
          v-model="form.clear_status"
          label="clear_status"
          :options="clearStatusOptions"
          :hint="clearHint"
        />

        <div class="grid grid-cols-1 gap-2">
          <SongPicker v-model="form.song_id" :candidates="songCandidates" :songs="songs" />
          <PartnerPicker
            v-model="form.partner_id"
            :candidates="partnerCandidates"
            :partners="partners"
          />
        </div>

        <div class="grid grid-cols-3 gap-2">
          <NumberField v-model="form.score" label="score" />
          <NumberField v-model="form.pure" label="pure" />
          <NumberField v-model="form.far" label="far" />
          <NumberField v-model="form.lost" label="lost" />
          <NumberField v-model="form.max_recall" label="max_recall" />
          <NumberField v-model="form.pure_shiny" label="pure_shiny" />
          <NumberField v-model="form.high_score" label="high_score" />
          <NumberField v-model="form.high_score_delta" label="high_score_delta" />
        </div>

        <div class="grid grid-cols-4 gap-2">
          <NumberField v-model="form.pure_early" label="pure_early" />
          <NumberField v-model="form.pure_late" label="pure_late" />
          <NumberField v-model="form.far_early" label="far_early" />
          <NumberField v-model="form.far_late" label="far_late" />
        </div>

        <CheckedToggle v-model="form.checked" class="mt-1" />
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
        <button class="btn" :disabled="busyAction !== null" @click="saveChecked">
          <i
            :class="
              busyAction === 'saveChecked'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-check size-4'
            "
          />
          确认并下一张
        </button>
        <button class="btn-secondary" :disabled="busyAction !== null" @click="saveAndNext">
          <i
            :class="
              busyAction === 'saveAndNext'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-save size-4'
            "
          />
          保存草稿并下一张
        </button>
        <button class="btn-secondary" :disabled="busyAction !== null" @click="skip">
          <i
            :class="
              busyAction === 'skip'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-skip-forward size-4'
            "
          />
          跳过
        </button>
      </div>
    </section>

    <ImageViewer
      :open="viewerOpen"
      :src="api.fileUrl(imageId)"
      :label="filename ?? imageId"
      :alt="filename ?? imageId"
      @close="viewerOpen = false"
    />
  </div>
</template>
