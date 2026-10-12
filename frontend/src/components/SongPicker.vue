<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxInput,
  ComboboxItem,
  ComboboxPortal,
  ComboboxRoot,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from "reka-ui";
import type { Candidate, SongEntry } from "../api";
import Button from "./Button.vue";

const props = defineProps<{
  candidates: Candidate[];
  songs: SongEntry[];
  modelValue: string | null;
  /** the song catalog is still loading; the panel shows a spinner
   * instead of a false "no matches" */
  loading?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const text = ref(props.modelValue ?? "");
const panelOpen = ref(false);
const query = ref("");

// free text is the value
watch(text, (value) => {
  emit("update:modelValue", value.trim() === "" ? null : value);
});

// prefill loads arrive after mount (and card switches swap the proposal)
watch(
  () => props.modelValue,
  (value) => {
    if (value !== text.value.trim()) text.value = value ?? "";
  },
);

const titleOf = computed(() => {
  const map = new Map(props.songs.map((s) => [s.id, s.title]));
  return (id: string) => map.get(id) ?? id;
});

const filteredSongs = computed(() => {
  const q = query.value.trim().toLowerCase();
  const all = props.songs;
  if (q === "") return all.slice(0, 80);
  return all
    .filter((s) => s.title.toLowerCase().includes(q) || s.id.toLowerCase().includes(q))
    .slice(0, 80);
});

// the single-select listbox deselects the picked candidate on re-click by
// emitting undefined; the field keeps its text in that case
function onSelect(value: unknown) {
  if (typeof value !== "string") return;
  text.value = value;
}

function selectFromPanel(id: string) {
  panelOpen.value = false;
  text.value = id;
}
</script>

<template>
  <ComboboxRoot
    :model-value="props.modelValue"
    :reset-search-term-on-blur="false"
    :reset-search-term-on-select="false"
    ignore-filter
    open-on-focus
    @update:model-value="onSelect"
  >
    <ComboboxAnchor class="flex items-end gap-1">
      <label class="block flex-1">
        <span class="field-label">song_id</span>
        <ComboboxInput v-model="text" class="field-input mt-0.5" placeholder="留空 = 未知" />
      </label>
      <Button variant="secondary" title="搜索全目录" @click="panelOpen = true">
        <i class="i-lucide-search size-4" />
        搜索
      </Button>
    </ComboboxAnchor>

    <!-- candidates are OCR proposals, not catalog entries, so they never
         filter against the typed text -->
    <ComboboxPortal v-if="props.candidates.length > 0">
      <ComboboxContent
        position="popper"
        :side-offset="4"
        class="z-10 w-[var(--reka-popper-anchor-width)] overflow-y-auto rounded border border-border bg-card shadow-lg"
      >
        <ComboboxItem
          v-for="c in props.candidates"
          :key="c.image_id"
          :value="c.image_id"
          class="flex cursor-pointer items-center justify-between gap-2 px-2 py-1.5 text-left text-sm data-[highlighted]:bg-secondary"
        >
          <span class="truncate">{{ titleOf(c.image_id) }}</span>
          <span class="shrink-0 text-xs text-muted-foreground">
            {{ c.image_id }} · {{ (c.confidence * 100).toFixed(1) }}%
          </span>
        </ComboboxItem>
      </ComboboxContent>
    </ComboboxPortal>
  </ComboboxRoot>

  <DialogRoot :open="panelOpen" @update:open="panelOpen = $event">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/60" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 max-h-full w-full max-w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-4 shadow-xl focus:outline-none"
      >
        <DialogTitle class="mb-2 text-sm font-semibold">搜索歌曲目录</DialogTitle>
        <DialogDescription class="sr-only">
          输入标题或 song_id 过滤，点击结果选择
        </DialogDescription>
        <input v-model="query" class="field-input" placeholder="标题或 song_id…" autofocus />
        <div class="mt-2 max-h-80 overflow-y-auto">
          <button
            v-for="s in filteredSongs"
            :key="s.id"
            type="button"
            class="flex w-full items-baseline justify-between gap-3 rounded px-2 py-1.5 text-left text-sm hover:bg-secondary"
            @click="selectFromPanel(s.id)"
          >
            <span class="truncate">{{ s.title }}</span>
            <span class="shrink-0 font-mono text-xs text-muted-foreground">
              {{ s.id }}
            </span>
          </button>
          <div
            v-if="props.loading"
            class="px-2 py-4 text-center text-sm text-muted-foreground"
            aria-busy="true"
          >
            <i class="i-lucide-loader-circle size-4 animate-spin" />
            目录加载中…
          </div>
          <div
            v-else-if="filteredSongs.length === 0"
            class="px-2 py-4 text-center text-sm text-muted-foreground"
          >
            无匹配结果
          </div>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
