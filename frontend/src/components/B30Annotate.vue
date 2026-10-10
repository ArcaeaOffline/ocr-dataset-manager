<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import {
  api,
  catalog,
  type B30ComponentFields,
  type B30ComponentPrefill,
  type B30LayoutInfo,
  type B30Result,
  type SongEntry,
} from "../api";
import NumberField from "../components/NumberField.vue";
import SegmentedSelect from "../components/SegmentedSelect.vue";
import SongPicker from "../components/SongPicker.vue";
import { useRequest } from "../composables/useRequest";

const route = useRoute();
const router = useRouter();

const imageId = computed(() => String(route.params.id));
const layout = ref<string | null>(null);
const currentIndex = ref(0);
const busyAction = ref<"saveChecked" | "saveDraft" | null>(null);

interface CardData {
  prefill: B30ComponentPrefill | null;
  saved: B30ComponentFields | null;
  /** a prefill request for this card is in flight */
  loading?: boolean;
}

const cardData = reactive<Record<number, CardData>>({});

function emptyComponent(index: number): B30ComponentFields {
  return {
    index,
    song_id: null,
    rating_class: null,
    score: null,
    pure: null,
    far: null,
    lost: null,
    pure_shiny: null,
    clear_status: null,
    checked: false,
  };
}

const form = reactive<B30ComponentFields>(emptyComponent(0));

const { data: layouts } = useRequest("b30-layouts", () => api.getB30Layouts(), {
  initialData: [] as B30LayoutInfo[],
});

const layoutOptions = computed(() => [
  { value: null, label: "未知" },
  ...layouts.value.map((l) => ({ value: l.id, label: l.id })),
]);
const ratingClassOptions = ["PST", "PRS", "FTR", "BYD", "ETR"].map((label, i) => ({
  value: i,
  label,
}));
// bots render all six st3 clear states; EC/HC never appear on device screenshots
const clearStatusOptions = ["TL", "TC", "FR", "PM", "EC", "HC"].map((label, i) => ({
  value: i,
  label,
}));

const componentCount = computed(() => {
  if (layout.value == null) return 0;
  return layouts.value.find((l) => l.id === layout.value)?.component_count ?? 0;
});

const { data, loading } = useRequest(
  imageId,
  async (id): Promise<B30Result | null> => {
    const [saved, prefillLayout] = await Promise.all([
      api.getB30Result(id).catch(() => null),
      api
        .getPrefill(id)
        .then((res) => (res.kind === "b30" ? res.layout : null))
        .catch(() => null),
    ]);
    layout.value = saved?.layout ?? prefillLayout;
    if (saved != null) {
      for (const component of saved.components) {
        cardData[component.index] = { prefill: null, saved: component };
      }
    }
    return saved;
  },
  { initialData: null },
);

const savedComponents = computed(() => data.value?.components ?? []);
const checkedCount = computed(() => savedComponents.value.filter((c) => c.checked).length);

function loadCard(index: number) {
  currentIndex.value = index;
  const cached = cardData[index];
  const merged: B30ComponentFields = { ...emptyComponent(index), ...cached?.prefill };
  if (cached?.saved != null) {
    for (const key of Object.keys(emptyComponent(index)) as (keyof B30ComponentFields)[]) {
      const value = cached.saved[key];
      if (key === "index" || key === "checked" || value != null) {
        (merged as unknown as Record<string, unknown>)[key] = value;
      }
    }
  }
  Object.assign(form, merged);
}

// the OCR proposal for a card is computed on first view (~0.4s), so the
// prefill fetch runs per card instead of for the whole screenshot
watch(
  [imageId, currentIndex],
  async ([id, index], previous) => {
    const [prevId] = previous ?? [null];
    if (prevId !== id) {
      for (const key of Object.keys(cardData)) delete cardData[Number(key)];
      // resetting currentIndex re-triggers this watch; the loading flag
      // below keeps the second run from fetching again
      index = 0;
      currentIndex.value = 0;
    }
    const existing = cardData[index];
    loadCard(index);
    if (existing?.prefill != null || existing?.loading) return;
    const fetchLayout = layout.value;
    cardData[index] = { prefill: null, saved: existing?.saved ?? null, loading: true };
    try {
      const prefill = await api.getB30ComponentPrefill(id, index);
      // a layout switch while the request ran invalidates the proposal
      if (fetchLayout === layout.value) {
        cardData[index] = { prefill, saved: existing?.saved ?? null, loading: false };
      }
    } catch (e) {
      toast.error(`预识别失败：${(e as Error).message}`);
    } finally {
      const entry = cardData[index];
      if (entry?.loading) cardData[index] = { ...entry, loading: false };
    }
    if (currentIndex.value === index && fetchLayout === layout.value) loadCard(index);
  },
  { immediate: true },
);

function onLayoutChange(value: string | null) {
  if (value === layout.value) return;
  layout.value = value;
  // prefills were computed on the old layout's grid; saved rows can
  // stay, the backend replaces them when the new layout is saved
  for (const key of Object.keys(cardData)) {
    const entry = cardData[Number(key)];
    cardData[Number(key)] = { ...entry, prefill: null, loading: false };
  }
  loadCard(currentIndex.value);
}

function previousCard() {
  if (currentIndex.value > 0) currentIndex.value--;
}

function nextCard() {
  if (layout.value == null || currentIndex.value < componentCount.value - 1) {
    currentIndex.value++;
  }
}

async function save(checked: boolean): Promise<boolean> {
  form.checked = checked;
  const layoutId = layout.value;
  if (layoutId == null) {
    toast.error("布局未知，无法保存");
    return false;
  }
  try {
    const saved = await api.saveB30Result(imageId.value, layoutId, [{ ...form }]);
    const updated = saved.components.find((c) => c.index === form.index) ?? null;
    cardData[form.index] = { ...cardData[form.index], saved: updated };
    // the queue's checked state is derived from the saved rows; data is a
    // shallow ref, so the components list must be replaced wholesale
    if (data.value != null) {
      data.value = {
        ...data.value,
        components: [
          ...data.value.components.filter((c) => c.index !== form.index),
          ...(updated ? [updated] : []),
        ],
      };
    }
    return true;
  } catch (e) {
    toast.error(`保存失败：${(e as Error).message}`);
    return false;
  }
}

async function saveChecked() {
  await withBusy("saveChecked", async () => {
    if (!(await save(true))) return;
    if (currentIndex.value >= componentCount.value - 1) {
      await goNext();
    } else {
      nextCard();
    }
  });
}

async function saveDraft() {
  await withBusy("saveDraft", async () => {
    await save(false);
  });
}

async function goNext() {
  let nextId: string | null;
  try {
    ({ id: nextId } = await api.getNextImage(imageId.value, "b30"));
  } catch (e) {
    toast.error(`获取下一张失败：${(e as Error).message}`);
    return;
  }
  if (nextId === null) {
    toast.success("没有未标注的 B30 图片了");
    await router.push("/");
    return;
  }
  await router.replace(`/annotate/${nextId}`);
}

async function withBusy(action: "saveChecked" | "saveDraft", run: () => Promise<void>) {
  if (busyAction.value !== null) return;
  busyAction.value = action;
  try {
    await run();
  } finally {
    busyAction.value = null;
  }
}

const filename = ref<string | null>(null);
const songs = ref<SongEntry[]>([]);
api
  .getImage(imageId.value)
  .then((image) => (filename.value = image.original_filename))
  .catch(() => null);
catalog
  .songs()
  .then((list) => (songs.value = list))
  .catch(() => null);

const ratingHint = computed(() => {
  const votes = cardData[currentIndex.value]?.prefill?.rating_class_votes;
  if (votes == null || votes.length < 2) return null;
  const sorted = [...votes].sort((a, b) => b - a);
  if ((sorted[1] ?? 0) > 0 && (sorted[0] ?? 0) - (sorted[1] ?? 0) <= 1) {
    return `预填投票接近：${votes.join(" / ")}`;
  }
  return null;
});

function onKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === "Enter") {
    void saveChecked();
    return;
  }
  // arrows move the caret inside text fields, so only flip cards outside them
  const target = event.target;
  if (
    target instanceof HTMLElement &&
    (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
  ) {
    return;
  }
  if (event.key === "ArrowLeft") previousCard();
  if (event.key === "ArrowRight") nextCard();
}

onMounted(() => {
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
    <section class="self-start">
      <div class="overflow-hidden rounded border border-border bg-card">
        <img
          :key="currentIndex"
          :src="api.b30CardUrl(imageId, currentIndex)"
          class="block max-h-[calc(100dvh-12rem)] w-full object-contain"
          :alt="`card ${currentIndex}`"
        />
      </div>
      <div class="mt-2 flex items-center justify-between gap-2">
        <button class="btn-secondary" :disabled="currentIndex === 0" @click="previousCard">
          <i class="i-lucide-arrow-left size-4" />
          上一卡
        </button>
        <span class="text-sm tabular-nums text-muted-foreground">
          卡 {{ currentIndex + 1 }} / {{ componentCount || "?" }} ·
          {{ layout ?? "布局未知" }}
        </span>
        <button
          class="btn-secondary"
          :disabled="layout != null && currentIndex >= componentCount - 1"
          @click="nextCard"
        >
          下一卡
          <i class="i-lucide-arrow-right size-4" />
        </button>
      </div>
      <p class="mt-1 break-all text-xs text-muted-foreground">{{ filename ?? imageId }}</p>
    </section>

    <section class="space-y-4">
      <div class="space-y-3 rounded border border-border bg-card p-3">
        <SegmentedSelect
          :model-value="layout"
          label="layout"
          :options="layoutOptions"
          @update:model-value="onLayoutChange"
        />
        <p class="text-xs text-muted-foreground">
          已确认 {{ checkedCount }} / {{ componentCount || "?" }} 卡
        </p>

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
        />
        <SongPicker
          v-model="form.song_id"
          :candidates="cardData[currentIndex]?.prefill?.song_id_candidates ?? []"
          :songs="songs"
        />

        <div class="grid grid-cols-3 gap-2">
          <NumberField v-model="form.score" label="score" />
          <NumberField v-model="form.pure" label="pure" />
          <NumberField v-model="form.pure_shiny" label="pure_shiny" />
          <NumberField v-model="form.far" label="far" />
          <NumberField v-model="form.lost" label="lost" />
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button class="btn" :disabled="busyAction !== null || layout == null" @click="saveChecked">
          <i
            :class="
              busyAction === 'saveChecked'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-check size-4'
            "
          />
          确认此卡{{ currentIndex >= componentCount - 1 ? "，下一图" : "" }}
        </button>
        <button
          class="btn-secondary"
          :disabled="busyAction !== null || layout == null"
          @click="saveDraft"
        >
          <i
            :class="
              busyAction === 'saveDraft'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-save size-4'
            "
          />
          保存草稿
        </button>
      </div>
    </section>
  </div>
</template>
