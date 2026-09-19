<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import { api, catalog, type Prefill, type ResultFields, type SongEntry } from "../api";
import NumberField from "../components/NumberField.vue";
import PartnerPicker from "../components/PartnerPicker.vue";
import SegmentedSelect from "../components/SegmentedSelect.vue";
import SongPicker from "../components/SongPicker.vue";
import { computeWarnings } from "../warnings";

const route = useRoute();
const router = useRouter();

const imageId = computed(() => String(route.params.id));
const filename = ref<string | null>(null);
const loading = ref(true);
const imgReady = ref(false);
const busyAction = ref<"saveChecked" | "saveAndNext" | "skip" | null>(null);

const songCandidates = ref<{ image_id: string; confidence: number }[]>([]);
const partnerCandidates = ref<{ image_id: string; confidence: number }[]>([]);
const songs = ref<SongEntry[]>([]);
const partners = ref<{ id: string }[]>([]);

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
const ratingClassOptions = ["PST", "PRS", "FTR", "BYD", "ETR"].map((label, i) => ({
  value: i,
  label: `${i} ${label}`,
}));
const clearStatusOptions = ["LOST", "CLEAR", "FR", "PM"].map((label, i) => ({
  value: i,
  label: `${i} ${label}`,
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

async function load() {
  loading.value = true;
  imgReady.value = false;
  try {
    const [prefill] = await Promise.all([
      api.getPrefill(imageId.value).catch((e: Error) => {
        toast.error(`预识别失败：${e.message}`);
        return null;
      }),
      catalog
        .songs()
        .then((s) => (songs.value = s))
        .catch(() => undefined),
      catalog
        .partners()
        .then((p) => (partners.value = p))
        .catch(() => undefined),
    ]);

    if (prefill != null) {
      applyPrefill(prefill);
      songCandidates.value = prefill.song_id_candidates ?? [];
      partnerCandidates.value = prefill.partner_id_candidates ?? [];
    }

    try {
      const saved = await api.getResult(imageId.value);
      // saved (draft) values win, but empty fields fall back to prefill
      const merged: ResultFields = { ...emptyFields(), ...prefill };
      for (const key of Object.keys(emptyFields()) as (keyof ResultFields)[]) {
        const value = saved[key];
        if (value != null) {
          (merged as Record<string, unknown>)[key] = value;
        }
      }
      Object.assign(form, merged);
    } catch {
      // not annotated yet; prefill stays
    }

    const list = await api.listImages(false, 0, 1);
    filename.value = list.items.find((it) => it.id === imageId.value)?.original_filename ?? null;
  } finally {
    loading.value = false;
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
  const data = await api.listImages(true, 0, 200);
  const ids = data.items.map((it) => it.id);
  if (ids.length === 0) {
    toast.success("没有未标注的图片了");
    await router.push("/");
    return;
  }
  const idx = ids.indexOf(imageId.value);
  const nextId = ids[(idx + 1) % ids.length];
  await router.replace(`/annotate/${nextId}`);
}

async function withBusy(action: "saveChecked" | "saveAndNext" | "skip", run: () => Promise<void>) {
  if (busyAction.value !== null) return;
  busyAction.value = action;
  try {
    await run();
  } finally {
    busyAction.value = null;
  }
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
}

watch(imageId, load);
onMounted(() => {
  load();
  window.addEventListener("keydown", onKeydown);
});
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <div v-if="loading" class="grid place-items-center py-24 text-muted-foreground" aria-busy="true">
    <i class="i-lucide-loader-circle size-6 animate-spin" />
  </div>
  <div v-else class="grid gap-4 py-4 lg:grid-cols-[1fr_360px]">
    <section class="lg:sticky lg:top-4 lg:self-start">
      <div class="relative">
        <img
          :src="api.fileUrl(imageId)"
          class="w-full rounded border border-border bg-card lg:max-h-[calc(100dvh-6rem)] lg:object-contain"
          :alt="filename ?? imageId"
          @load="imgReady = true"
        />
        <div
          v-if="!imgReady"
          class="absolute inset-0 grid place-items-center rounded border border-border bg-card text-muted-foreground"
        >
          <i class="i-lucide-loader-circle size-6 animate-spin" />
        </div>
      </div>
      <p class="mt-1 text-xs text-muted-foreground">{{ filename ?? imageId }}</p>
    </section>

    <section class="space-y-4">
      <div class="rounded border border-border bg-card p-3 space-y-3">
        <SegmentedSelect v-model="form.rois_type" label="rois_type" :options="roisTypeOptions" />
        <SegmentedSelect
          v-model="form.rating_class"
          label="rating_class"
          :options="ratingClassOptions"
        />
        <SegmentedSelect
          v-model="form.clear_status"
          label="clear_status"
          :options="clearStatusOptions"
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

      <div class="flex justify-end">
        <label class="flex items-center gap-1.5 text-sm">
          <input v-model="form.checked" type="checkbox" />
          checked
        </label>
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
  </div>
</template>
