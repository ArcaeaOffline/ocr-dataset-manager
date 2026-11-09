<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { api } from "@/api";
import FullscreenDialog from "@/components/ui/FullscreenDialog.vue";
import { useShortcuts } from "@/composables/useShortcuts";
import { gridMove, type GridMoveKey } from "@/features/annotate/lib/overviewNav";

const props = defineProps<{
  open: boolean;
  imageId: string;
  layout: string | null;
  componentCount: number;
  currentIndex: number;
  /** card indexes whose saved row is checked */
  checkedIndexes: Set<number>;
}>();

const emit = defineEmits<{
  close: [];
  select: [index: number];
}>();

const highlight = ref(0);
const gridEl = ref<HTMLElement | null>(null);

watch(
  () => props.open,
  (open) => {
    if (open) highlight.value = props.currentIndex;
  },
);

// the responsive classes decide the column count, so read it off the
// rendered grid instead of duplicating the breakpoints
function columnCount(): number {
  const template = gridEl.value ? getComputedStyle(gridEl.value).gridTemplateColumns : "";
  return template.split(" ").length || 1;
}

function move(key: GridMoveKey) {
  if (props.componentCount === 0) return;
  highlight.value = gridMove(highlight.value, props.componentCount, columnCount(), key);
  void nextTick(() => {
    gridEl.value?.querySelector('[data-active="true"]')?.scrollIntoView({ block: "nearest" });
  });
}

// this dialog counts as open, so the composable-wide gate must stay off
useShortcuts(
  () => [
    { key: "arrowleft", handler: () => move("arrowleft") },
    { key: "arrowright", handler: () => move("arrowright") },
    { key: "arrowup", handler: () => move("arrowup") },
    { key: "arrowdown", handler: () => move("arrowdown") },
    {
      key: "enter",
      // a focused tile or the close button keep their native Enter
      enabled: () => !(document.activeElement instanceof HTMLButtonElement),
      handler: () => emit("select", highlight.value),
    },
  ],
  { enabled: () => props.open, dialogGated: false },
);
</script>

<template>
  <FullscreenDialog
    :open="props.open"
    title="卡片总览"
    description="点击卡片跳到对应卡"
    @close="emit('close')"
  >
    <template #header>
      <span class="text-xs">
        卡片总览 · {{ props.layout ?? "布局未知" }} · 已确认 {{ props.checkedIndexes.size }} /
        {{ props.componentCount }}
      </span>
    </template>
    <div class="flex-1 overflow-auto p-2">
      <div ref="gridEl" class="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-7">
        <button
          v-for="index in props.componentCount"
          :key="index"
          type="button"
          :data-active="index - 1 === highlight ? 'true' : undefined"
          class="focus-ring relative cursor-pointer overflow-hidden rounded border bg-card"
          :class="index - 1 === highlight ? 'border-ring ring-2 ring-ring' : 'border-border'"
          @click="emit('select', index - 1)"
        >
          <img
            :src="api.b30CardUrl(props.imageId, index - 1, props.layout ?? undefined)"
            class="block aspect-[2/1] w-full object-contain"
            loading="lazy"
            :alt="`card ${index - 1}`"
          />
          <!-- literal black mask: alpha modifiers drop on var()-based tokens -->
          <span
            v-if="props.checkedIndexes.has(index - 1)"
            class="absolute inset-0 flex items-center justify-center bg-black/50 text-white"
          >
            <i class="i-lucide-check size-6" />
          </span>
          <span
            class="absolute left-1 top-1 z-10 rounded bg-black/60 px-1 text-[10px] tabular-nums text-white"
          >
            {{ index }}
          </span>
        </button>
      </div>
    </div>
  </FullscreenDialog>
</template>
