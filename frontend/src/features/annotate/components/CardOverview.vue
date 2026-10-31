<script setup lang="ts">
import { api } from "@/api";
import FullscreenDialog from "@/components/ui/FullscreenDialog.vue";

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
      <div class="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-7">
        <button
          v-for="index in props.componentCount"
          :key="index"
          type="button"
          class="relative cursor-pointer overflow-hidden rounded border bg-card"
          :class="
            index - 1 === props.currentIndex ? 'border-ring ring-2 ring-ring' : 'border-border'
          "
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
