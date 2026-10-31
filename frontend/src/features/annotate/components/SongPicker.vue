<script setup lang="ts">
import { computed } from "vue";
import { ComboboxItem } from "reka-ui";
import type { Candidate, SongEntry } from "@/api";
import ComboboxPicker from "@/components/ui/ComboboxPicker.vue";

const props = defineProps<{
  candidates: Candidate[];
  songs: SongEntry[];
  modelValue: string | null;
  /** the song catalog is still loading. The panel shows a spinner
   * instead of a false "no matches" */
  loading?: boolean;
  /** the value is the machine prefill proposal. Shows a marker by the label */
  prefilled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const titleOf = computed(() => {
  const map = new Map(props.songs.map((s) => [s.id, s.title]));
  return (id: string) => map.get(id) ?? id;
});
</script>

<template>
  <ComboboxPicker
    :candidates="props.candidates"
    :model-value="props.modelValue"
    :prefilled="props.prefilled"
    label="song_id"
    placeholder="留空 = 未知"
    trigger-icon="i-lucide-search"
    trigger-label="搜索"
    trigger-title="搜索全目录"
    panel-title="搜索歌曲目录"
    panel-placeholder="标题或 song_id…"
    panel-description="输入标题或 song_id 过滤，点击结果选择"
    :panel-items="props.songs"
    :panel-match="(s, q) => s.title.toLowerCase().includes(q) || s.id.toLowerCase().includes(q)"
    :panel-limit="80"
    :panel-loading="props.loading ?? false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #options="{ candidates }">
      <ComboboxItem
        v-for="c in candidates"
        :key="c.image_id"
        :value="c.image_id"
        class="combobox-item justify-between"
      >
        <span class="truncate">{{ titleOf(c.image_id) }}</span>
        <span class="shrink-0 text-xs text-muted-foreground">
          {{ c.image_id }} · {{ (c.confidence * 100).toFixed(1) }}%
        </span>
      </ComboboxItem>
    </template>
    <template #panel="{ matches, select }">
      <button
        v-for="s in matches"
        :key="s.id"
        type="button"
        class="flex w-full items-baseline justify-between gap-3 rounded px-2 py-1.5 text-left text-sm hover:bg-accent"
        @click="select(s.id)"
      >
        <span class="truncate">{{ s.title }}</span>
        <span class="shrink-0 font-mono text-xs text-muted-foreground">
          {{ s.id }}
        </span>
      </button>
    </template>
  </ComboboxPicker>
</template>
