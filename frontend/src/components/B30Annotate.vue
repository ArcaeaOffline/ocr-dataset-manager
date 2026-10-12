<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import {
  api,
  catalog,
  CLEAR_STATUS_NAMES,
  RATING_CLASS_NAMES,
  type B30ComponentFields,
  type B30ComponentPrefill,
  type B30LayoutInfo,
  type B30Result,
  type SongEntry,
} from "../api";
import NumberField from "../components/NumberField.vue";
import Button from "../components/Button.vue";
import CardOverview from "../components/CardOverview.vue";
import CheckedToggle from "../components/CheckedToggle.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import FlowSelector from "../components/FlowSelector.vue";
import ImageViewer from "../components/ImageViewer.vue";
import LoadingMask from "../components/LoadingMask.vue";
import SegmentedSelect from "../components/SegmentedSelect.vue";
import SongPicker from "../components/SongPicker.vue";
import { useBusy } from "../composables/useBusy";
import { prefilledKeys, useFieldSources } from "../composables/useFieldSources";
import { useRequest } from "../composables/useRequest";
import { voteHint } from "../warnings";

const route = useRoute();
const router = useRouter();

const props = defineProps<{ flow: "device" | "b30" }>();

const emit = defineEmits<{
  switch: [flow: "device" | "b30"];
}>();

const imageId = computed(() => String(route.params.id));
const layout = ref<string | null>(null);
const currentIndex = ref(0);
const { busyAction, withBusy } = useBusy<"saveChecked" | "saveDraft" | "skip">();
const cardReady = ref(false);
const viewerOpen = ref(false);
const overviewOpen = ref(false);

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

const { form, prefilled, markPrefilled } = useFieldSources(
  reactive<B30ComponentFields>(emptyComponent(0)),
);

// fields that can carry a prefill mark; index is not a rendered field and
// checked has no proposal
const sourceKeys = Object.keys(emptyComponent(0)).filter(
  (key) => key !== "index" && key !== "checked",
) as (keyof B30ComponentFields)[];

const { data: layouts } = useRequest("b30-layouts", () => api.getB30Layouts(), {
  initialData: [] as B30LayoutInfo[],
});

const layoutOptions = computed(() => [
  { value: null, label: "未知" },
  ...layouts.value.map((l) => ({ value: l.id, label: l.id })),
]);
const ratingClassOptions = RATING_CLASS_NAMES.map((label, i) => ({ value: i, label }));
// bots render all six st3 clear states; EC/HC never appear on device screenshots
const clearStatusOptions = CLEAR_STATUS_NAMES.map((label, i) => ({ value: i, label }));

const componentCount = computed(() => {
  if (layout.value == null) return 0;
  return layouts.value.find((l) => l.id === layout.value)?.component_count ?? 0;
});

const filename = ref<string | null>(null);
const songs = ref<SongEntry[]>([]);
const songsLoading = ref(true);

const { data, loading } = useRequest(
  imageId,
  async (id): Promise<B30Result | null> => {
    const [saved, prefillLayout, image] = await Promise.all([
      api.getB30Result(id).catch(() => null),
      api
        .getPrefill(id)
        .then((res) => (res.kind === "b30" ? res.layout : null))
        .catch(() => null),
      api.getImage(id).catch(() => null),
    ]);
    filename.value = image?.original_filename ?? null;
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

catalog
  .songs()
  .then((list) => (songs.value = list))
  .catch(() => null)
  .finally(() => (songsLoading.value = false));

const savedComponents = computed(() => data.value?.components ?? []);
const checkedCount = computed(() => savedComponents.value.filter((c) => c.checked).length);
const checkedIndexes = computed(
  () => new Set(savedComponents.value.filter((c) => c.checked).map((c) => c.index)),
);

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
  markPrefilled(prefilledKeys(sourceKeys, cached?.saved, cached?.prefill));
}

// the OCR proposal for a card is computed on first view (~0.4s), so the
// prefill fetch runs per card instead of for the whole screenshot
async function fetchCardPrefill(id: string, index: number) {
  const existing = cardData[index];
  if (existing?.prefill != null || existing?.loading) return;
  // without a layout there is nothing to OCR against; the card area
  // shows a hint instead
  if (layout.value == null) return;
  const fetchLayout = layout.value;
  cardData[index] = { prefill: null, saved: existing?.saved ?? null, loading: true };
  try {
    const prefill = await api.getB30ComponentPrefill(id, index, fetchLayout ?? undefined);
    // an image or layout switch while the request ran invalidates the proposal
    if (id === imageId.value && fetchLayout === layout.value) {
      cardData[index] = { prefill, saved: existing?.saved ?? null, loading: false };
    }
  } catch (e) {
    toast.error(`预识别失败：${(e as Error).message}`);
  } finally {
    if (id === imageId.value) {
      const entry = cardData[index];
      if (entry?.loading) cardData[index] = { ...entry, loading: false };
    }
  }
  if (id === imageId.value && currentIndex.value === index && fetchLayout === layout.value) {
    loadCard(index);
  }
}

watch(
  [imageId, currentIndex],
  async ([id, index], previous) => {
    const [prevId] = previous ?? [null];
    if (prevId !== id) {
      for (const key of Object.keys(cardData)) delete cardData[Number(key)];
      // resetting currentIndex re-triggers this watch; the loading flag
      // in fetchCardPrefill keeps the second run from fetching again
      index = 0;
      currentIndex.value = 0;
    }
    cardReady.value = false;
    loadCard(index);
    await fetchCardPrefill(id, index);
  },
  { immediate: true },
);

async function onLayoutChange(value: string | null) {
  if (value === layout.value) return;
  if (value == null) {
    // 未知: local-only switch; saved rows stay on the server, and saving
    // requires a layout anyway
    layout.value = null;
    for (const key of Object.keys(cardData)) {
      const entry = cardData[Number(key)];
      cardData[Number(key)] = { ...entry, prefill: null, loading: false };
    }
    loadCard(currentIndex.value);
    return;
  }
  if (savedComponents.value.length > 0) {
    pendingLayout.value = value;
    return;
  }
  await applyLayoutSwitch(value);
}

// a layout switch awaiting confirmation; non-null opens the confirm dialog
const pendingLayout = ref<string | null>(null);
const switchingLayout = ref(false);

function confirmPendingLayout() {
  if (pendingLayout.value == null) return;
  void applyLayoutSwitch(pendingLayout.value);
}

async function applyLayoutSwitch(value: string) {
  const previous = layout.value;
  layout.value = value;
  cardReady.value = false;
  switchingLayout.value = true;
  try {
    // persist the new layout immediately; the backend drops the old
    // layout's component rows when a PUT arrives with a different layout,
    // so the server state matches the UI right away
    data.value = await api.saveB30Result(imageId.value, value, []);
  } catch (e) {
    toast.error(`切换布局失败：${(e as Error).message}`);
    layout.value = previous;
    return;
  } finally {
    switchingLayout.value = false;
    pendingLayout.value = null;
  }
  for (const key of Object.keys(cardData)) delete cardData[Number(key)];
  // the new layout may render fewer cards than the index currently points at
  if (componentCount.value > 0 && currentIndex.value >= componentCount.value) {
    currentIndex.value = componentCount.value - 1;
  }
  loadCard(currentIndex.value);
  void fetchCardPrefill(imageId.value, currentIndex.value);
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
  // the form holds the previous image's values until the load lands
  if (loading.value) return;
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
  if (loading.value) return;
  await withBusy("saveDraft", async () => {
    await save(false);
  });
}

async function skip() {
  if (loading.value) return;
  await withBusy("skip", goNext);
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

function selectCard(index: number) {
  overviewOpen.value = false;
  currentIndex.value = index;
}

const ratingHint = computed(() =>
  voteHint(cardData[currentIndex.value]?.prefill?.rating_class_votes),
);

function onKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === "Enter") {
    void saveChecked();
    return;
  }
  const target = event.target;
  // arrows flip cards, but text fields need them for the caret and
  // role=group widgets (SegmentedSelect) for roving focus — yield to both
  const inTextField =
    target instanceof HTMLElement &&
    (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
  const inRovingFocusGroup =
    target instanceof HTMLElement && target.closest('[role="group"]') != null;
  if (event.key === "Escape" && !inTextField) {
    viewerOpen.value = false;
    overviewOpen.value = false;
  }
  if (!inTextField && !inRovingFocusGroup) {
    if (event.key === "ArrowLeft") previousCard();
    if (event.key === "ArrowRight") nextCard();
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
  <!-- the form stays mounted under the mask: picker inputs sync through
       modelValue watches that a mount/unmount swap would bypass -->
  <div class="relative grid gap-4 py-4 lg:grid-cols-[1fr_360px]">
    <section
      class="sticky top-0 z-10 self-start bg-background pb-1 lg:top-4 lg:z-0 lg:bg-transparent lg:pb-0"
    >
      <FlowSelector
        :flow="flow"
        :layout="layout"
        :layout-options="layoutOptions"
        @switch="emit('switch', $event)"
        @change-layout="onLayoutChange"
      />
      <div class="relative mt-2 min-h-40 overflow-hidden rounded border border-border bg-card">
        <img
          :key="currentIndex"
          :src="api.b30CardUrl(imageId, currentIndex, layout ?? undefined)"
          class="mx-auto block max-h-[calc(100dvh-12rem)] max-w-full cursor-zoom-in object-contain"
          :alt="`card ${currentIndex}`"
          title="点击打开卡片总览"
          @load="cardReady = true"
          @error="cardReady = true"
          @click="overviewOpen = true"
        />
        <div
          v-if="!cardReady"
          class="absolute inset-0 grid place-items-center bg-card text-muted-foreground"
        >
          <i class="i-lucide-loader-circle size-6 animate-spin" />
        </div>
        <div
          v-if="layout == null"
          class="absolute inset-0 grid place-items-center bg-card p-4 text-center text-sm text-muted-foreground"
        >
          布局未知，请在上方选择样式
        </div>
      </div>
      <div class="mt-2 flex items-center justify-between gap-2">
        <Button variant="secondary" :disabled="currentIndex === 0" @click="previousCard">
          <i class="i-lucide-arrow-left size-4" />
          上一卡
        </Button>
        <div class="flex items-center gap-1">
          <span class="text-sm tabular-nums text-muted-foreground">
            卡 {{ currentIndex + 1 }} / {{ componentCount || "?" }}
          </span>
          <button
            type="button"
            class="cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            title="查看完整截图"
            @click="viewerOpen = true"
          >
            <i class="i-lucide-expand size-4" />
          </button>
          <button
            type="button"
            class="cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            title="卡片总览"
            :disabled="layout == null"
            @click="overviewOpen = true"
          >
            <i class="i-lucide-layout-grid size-4" />
          </button>
        </div>
        <Button
          variant="secondary"
          :disabled="layout != null && currentIndex >= componentCount - 1"
          @click="nextCard"
        >
          下一卡
          <i class="i-lucide-arrow-right size-4" />
        </Button>
      </div>
      <p class="mt-1 break-all text-xs text-muted-foreground">{{ filename ?? imageId }}</p>
    </section>

    <section class="space-y-4">
      <div class="relative space-y-3 rounded border border-border bg-card p-3">
        <p class="text-xs text-muted-foreground">
          已确认 {{ checkedCount }} / {{ componentCount || "?" }} 卡
        </p>

        <SegmentedSelect
          v-model="form.rating_class"
          label="rating_class"
          :options="ratingClassOptions"
          :hint="ratingHint"
          :prefilled="prefilled.has('rating_class')"
        />
        <SegmentedSelect
          v-model="form.clear_status"
          label="clear_status"
          :options="clearStatusOptions"
          :prefilled="prefilled.has('clear_status')"
        />
        <SongPicker
          v-model="form.song_id"
          :candidates="cardData[currentIndex]?.prefill?.song_id_candidates ?? []"
          :songs="songs"
          :loading="songsLoading"
          :prefilled="prefilled.has('song_id')"
        />

        <div class="grid grid-cols-3 gap-2">
          <NumberField v-model="form.score" label="score" :prefilled="prefilled.has('score')" />
          <NumberField v-model="form.pure" label="pure" :prefilled="prefilled.has('pure')" />
          <NumberField
            v-model="form.pure_shiny"
            label="pure_shiny"
            :prefilled="prefilled.has('pure_shiny')"
          />
          <NumberField v-model="form.far" label="far" :prefilled="prefilled.has('far')" />
          <NumberField v-model="form.lost" label="lost" :prefilled="prefilled.has('lost')" />
        </div>

        <CheckedToggle v-model="form.checked" class="mt-1" />

        <LoadingMask v-if="cardData[currentIndex]?.loading" tone="card" size="size-5" />
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <Button :disabled="busyAction !== null || layout == null" @click="saveChecked">
          <i
            :class="
              busyAction === 'saveChecked'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-check size-4'
            "
          />
          确认并{{ currentIndex >= componentCount - 1 ? "下一图" : "下一卡" }}
        </Button>
        <Button
          variant="secondary"
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
        </Button>
        <Button variant="secondary" :disabled="busyAction !== null" @click="skip">
          <i
            :class="
              busyAction === 'skip'
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-skip-forward size-4'
            "
          />
          跳过此图
        </Button>
      </div>
    </section>

    <ConfirmDialog
      :open="pendingLayout != null"
      title="切换布局"
      :description="
        pendingLayout == null
          ? ''
          : `按 ${pendingLayout} 重新切分这张图的卡片，已保存的 ${savedComponents.length} 张卡标注将被清空。`
      "
      confirm-label="确认切换"
      destructive
      :busy="switchingLayout"
      @update:open="
        (open: boolean) => {
          if (!open) pendingLayout = null;
        }
      "
      @confirm="confirmPendingLayout"
    />

    <ImageViewer
      :open="viewerOpen"
      :src="api.fileUrl(imageId)"
      :label="filename ?? imageId"
      :alt="filename ?? imageId"
      @close="viewerOpen = false"
    />
    <CardOverview
      :open="overviewOpen"
      :image-id="imageId"
      :layout="layout"
      :component-count="componentCount"
      :current-index="currentIndex"
      :checked-indexes="checkedIndexes"
      @close="overviewOpen = false"
      @select="selectCard"
    />

    <LoadingMask v-if="loading" tone="page" />
  </div>
</template>
