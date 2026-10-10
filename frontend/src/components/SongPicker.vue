<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Candidate, SongEntry } from "../api";
import Modal from "./Modal.vue";

const props = defineProps<{
  candidates: Candidate[];
  songs: SongEntry[];
  modelValue: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const text = ref(props.modelValue ?? "");
// prefill loads arrive after mount (and card switches swap the proposal)
watch(
  () => props.modelValue,
  (value) => {
    if (value !== text.value.trim()) text.value = value ?? "";
  },
);
const open = ref(false);
const panelOpen = ref(false);
const query = ref("");

const titleOf = computed(() => {
  const map = new Map(props.songs.map((s) => [s.id, s.title]));
  return (id: string) => map.get(id) ?? id;
});

function onInput(event: Event) {
  text.value = (event.target as HTMLInputElement).value;
  open.value = true;
  emit("update:modelValue", text.value.trim() === "" ? null : text.value);
}

function pick(id: string) {
  text.value = id;
  emit("update:modelValue", id);
  open.value = false;
}

function onBlur() {
  setTimeout(() => {
    open.value = false;
  }, 120);
}

const filteredSongs = computed(() => {
  const q = query.value.trim().toLowerCase();
  const all = props.songs;
  if (q === "") return all.slice(0, 80);
  return all
    .filter((s) => s.title.toLowerCase().includes(q) || s.id.toLowerCase().includes(q))
    .slice(0, 80);
});

function selectFromPanel(id: string) {
  panelOpen.value = false;
  pick(id);
}
</script>

<template>
  <div class="relative">
    <div class="flex items-end gap-1">
      <label class="block flex-1">
        <span class="field-label">song_id</span>
        <input
          class="field-input mt-0.5"
          :value="text"
          placeholder="留空 = 未知"
          @input="onInput"
          @focus="open = true"
          @blur="onBlur"
        />
      </label>
      <button class="btn-secondary" title="搜索全目录" @click="panelOpen = true">
        <i class="i-lucide-search size-4" />
        搜索
      </button>
    </div>
    <div
      v-if="open && props.candidates.length > 0"
      class="absolute z-10 mt-0.5 w-full overflow-y-auto rounded border border-border bg-card shadow-lg"
    >
      <button
        v-for="c in props.candidates"
        :key="c.image_id"
        type="button"
        class="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-sm hover:bg-secondary"
        @mousedown.prevent="pick(c.image_id)"
      >
        <span class="truncate">{{ titleOf(c.image_id) }}</span>
        <span class="shrink-0 text-xs text-muted-foreground">
          {{ c.image_id }} · {{ (c.confidence * 100).toFixed(1) }}%
        </span>
      </button>
    </div>

    <Modal v-if="panelOpen" @close="panelOpen = false">
      <h3 class="mb-2 text-sm font-semibold">搜索歌曲目录</h3>
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
          v-if="filteredSongs.length === 0"
          class="px-2 py-4 text-center text-sm text-muted-foreground"
        >
          无匹配结果
        </div>
      </div>
    </Modal>
  </div>
</template>
