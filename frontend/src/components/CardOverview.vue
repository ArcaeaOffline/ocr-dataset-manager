<script setup lang="ts">
import { DialogContent, DialogDescription, DialogPortal, DialogRoot, DialogTitle } from "reka-ui";
import { api } from "../api";

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
  <DialogRoot :open="props.open" @update:open="(value) => !value && emit('close')">
    <DialogPortal>
      <DialogContent class="fixed inset-0 z-50 flex flex-col bg-black/90 focus:outline-none">
        <DialogTitle class="sr-only">卡片总览</DialogTitle>
        <DialogDescription class="sr-only">点击卡片跳到对应卡</DialogDescription>
        <div class="flex items-center justify-between gap-2 p-2 text-white">
          <span class="text-xs">
            卡片总览 · {{ props.layout ?? "布局未知" }} · 已确认 {{ props.checkedIndexes.size }} /
            {{ props.componentCount }}
          </span>
          <button
            type="button"
            class="cursor-pointer rounded p-1.5 hover:bg-white/10"
            @click="emit('close')"
          >
            <i class="i-lucide-x size-4" />
          </button>
        </div>
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
              <span
                v-if="props.checkedIndexes.has(index - 1)"
                class="absolute right-1 top-1 grid size-4 place-items-center rounded-full bg-primary text-primary-fg"
              >
                <i class="i-lucide-check size-3" />
              </span>
              <span
                class="absolute left-1 top-1 rounded bg-black/60 px-1 text-[10px] tabular-nums text-white"
              >
                {{ index }}
              </span>
            </button>
          </div>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
